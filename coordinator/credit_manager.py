"""
Grid-X Coordinator - Time-based credit/balance system.
Credits are based on compute time: you pay for seconds used; workers earn for seconds provided.
Reserve max at submit, then settle (refund unused + pay worker) when job completes.
"""

import os
import logging
from typing import Optional

from .database import get_db, now, db_get_job

logger = logging.getLogger(__name__)

# ----- Time-based rates (env-configurable) -----
# Cost per second of compute (charged to job submitter)
COST_PER_SECOND = float(os.getenv("GRIDX_COST_PER_SECOND", "0.1"))
# Minimum charge per job (so very short jobs still have a small cost)
MIN_COST = float(os.getenv("GRIDX_MIN_COST", "0.05"))
# Maximum charge per job (cap so one long job doesn't drain the account)
MAX_COST = float(os.getenv("GRIDX_MAX_COST", "25.0"))
# Fraction of submitter's cost that goes to the worker owner (0.0 to 1.0)
REWARD_RATIO = float(os.getenv("GRIDX_REWARD_RATIO", "0.85"))
# Default job timeout in seconds (used to compute max reserve when not provided)
DEFAULT_JOB_TIMEOUT = int(os.getenv("GRIDX_DEFAULT_JOB_TIMEOUT", "60"))
# Starting balance for new users
DEFAULT_INITIAL_BALANCE = float(os.getenv("GRIDX_INITIAL_CREDITS", "100.0"))


def ensure_user(user_id: str, initial_balance: Optional[float] = None) -> float:
    """Ensure user exists; create with initial balance if not. Returns current balance."""
    if initial_balance is None:
        initial_balance = DEFAULT_INITIAL_BALANCE
    DB = get_db()
    row = DB.execute(
        "SELECT balance FROM user_credits WHERE user_id=?", (user_id,)
    ).fetchone()
    if row is not None:
        return float(row[0])
    DB.execute(
        "INSERT INTO user_credits(user_id, balance, last_updated) VALUES(?,?,?)",
        (user_id, initial_balance, now()),
    )
    DB.commit()
    return initial_balance


def get_balance(user_id: str) -> float:
    """Return current balance; 0 if user does not exist."""
    row = get_db().execute(
        "SELECT balance FROM user_credits WHERE user_id=?", (user_id,)
    ).fetchone()
    if row is None:
        return 0.0
    return float(row[0])


def deduct(user_id: str, amount: float) -> bool:
    """Deduct amount from user's balance. Returns True if successful."""
    if amount <= 0:
        return True
    DB = get_db()
    cur = DB.execute(
        "UPDATE user_credits SET balance=balance-?, last_updated=? WHERE user_id=? AND balance>=?",
        (amount, now(), user_id, amount),
    )
    DB.commit()
    return cur.rowcount > 0


def credit(user_id: str, amount: float) -> None:
    """Add amount to user's balance. Creates user with 0 if not present."""
    if amount <= 0:
        return
    DB = get_db()
    ensure_user(user_id, initial_balance=0.0)
    DB.execute(
        "UPDATE user_credits SET balance=balance+?, last_updated=? WHERE user_id=?",
        (amount, now(), user_id),
    )
    DB.commit()


# ----- Time-based cost / reward -----


def compute_cost(duration_seconds: float) -> float:
    """
    Compute actual cost from duration (in seconds).
    Clamped to [MIN_COST, MAX_COST]. Uses MIN_COST if duration is missing or negative.
    """
    if duration_seconds is None or duration_seconds < 0:
        return MIN_COST
    raw = duration_seconds * COST_PER_SECOND
    return max(MIN_COST, min(MAX_COST, round(raw, 4)))


def compute_reward(actual_cost: float) -> float:
    """Compute reward to worker owner from actual cost paid by submitter."""
    if actual_cost <= 0:
        return 0.0
    return round(actual_cost * REWARD_RATIO, 4)


def get_max_reserve(timeout_seconds: Optional[int] = None) -> float:
    """
    Return the maximum amount to reserve at job submit (based on timeout).
    This is deducted upfront; unused portion is refunded when job completes.
    """
    timeout = timeout_seconds if timeout_seconds is not None else DEFAULT_JOB_TIMEOUT
    if timeout <= 0:
        timeout = DEFAULT_JOB_TIMEOUT
    raw = timeout * COST_PER_SECOND
    return min(MAX_COST, max(MIN_COST, round(raw, 4)))


def settle_job(
    job_id: str,
    worker_owner_id: Optional[str],
    duration_seconds: Optional[float],
) -> None:
    """
    Settle credits when a job completes (time-based).
    - Gets job's user_id and reserved amount (stored in job.cost at creation).
    - Computes actual cost from duration; refunds (reserved - actual) to submitter.
    - Credits worker owner (actual_cost * REWARD_RATIO).
    - Updates job row with duration_seconds and actual cost (for records).
    """
    job = db_get_job(job_id)
    if not job:
        logger.warning(f"settle_job: Job {job_id} not found")
        return

    user_id = (job.get("user_id") or "").strip()
    reserved = float(job.get("cost") or 0)
    if reserved <= 0:
        reserved = MAX_COST

    actual_cost = compute_cost(duration_seconds)
    refund = max(0.0, reserved - actual_cost)
    reward = compute_reward(actual_cost)

    # Refund unused reserve to submitter
    if refund > 0 and user_id:
        credit(user_id, refund)
        logger.info(f"settle_job: Job {job_id} refunded {refund} to {user_id} (reserved={reserved}, actual={actual_cost})")

    # Pay worker owner
    if reward > 0 and worker_owner_id and (worker_owner_id or "").strip():
        owner_id = (worker_owner_id or "").strip()
        if owner_id:
            credit(owner_id, reward)
            logger.info(f"settle_job: Job {job_id} credited {reward} to worker owner {owner_id}")

    # Persist duration and actual cost on job (database module will do this if we pass it)
    conn = get_db()
    try:
        conn.execute(
            """
            UPDATE jobs SET duration_seconds=?, cost=?
            WHERE id=?
            """,
            (duration_seconds if duration_seconds is not None else 0.0, actual_cost, job_id),
        )
        conn.commit()
    except Exception as e:
        # Column duration_seconds might not exist yet; log and continue
        logger.debug(f"settle_job: Could not update job duration/cost: {e}")


# ----- Backward compatibility for callers that expect fixed cost/reward -----


def get_job_cost() -> float:
    """Return max reserve (used when no timeout provided). Kept for API compatibility."""
    return get_max_reserve(DEFAULT_JOB_TIMEOUT)


def get_worker_reward() -> float:
    """Return typical reward for one unit of cost. Kept for API compatibility."""
    return compute_reward(1.0)
