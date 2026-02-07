"""
Grid-X Coordinator - Credit/balance system.
Tokens decrease when you use compute; they increase when your compute is used by others.
"""

import os
from typing import Optional

from .database import get_db, now

# Default starting balance for new users
DEFAULT_INITIAL_BALANCE = float(os.getenv("GRIDX_INITIAL_CREDITS", "100.0"))
# Cost per job (deducted from submitter)
JOB_COST = float(os.getenv("GRIDX_JOB_COST", "1.0"))
# Reward to worker owner when their worker runs a job
WORKER_REWARD = float(os.getenv("GRIDX_WORKER_REWARD", "0.8"))


def ensure_user(user_id: str, initial_balance: Optional[float] = None) -> float:
    """
    Ensure user exists in user_credits; if not, create with initial balance.
    Returns current balance.
    """
    if initial_balance is None:
        initial_balance = DEFAULT_INITIAL_BALANCE
    DB = get_db()
    row = DB.execute(
        "SELECT balance FROM user_credits WHERE user_id=?", (user_id,)
    ).fetchone()
    if row is not None:
        return float(row[0])
    DB.execute(
        "INSERT INTO user_credits(user_id, balance, updated_at) VALUES(?,?,?)",
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
    """
    Deduct amount from user's balance. Returns True if successful, False if insufficient.
    """
    if amount <= 0:
        return True
    DB = get_db()
    cur = DB.execute(
        "UPDATE user_credits SET balance=balance-?, updated_at=? WHERE user_id=? AND balance>=?",
        (amount, now(), user_id, amount),
    )
    DB.commit()
    return cur.rowcount > 0


def credit(user_id: str, amount: float) -> None:
    """Add amount to user's balance. Creates user with 0 if not present, then adds."""
    if amount <= 0:
        return
    DB = get_db()
    ensure_user(user_id, initial_balance=0.0)
    DB.execute(
        "UPDATE user_credits SET balance=balance+?, updated_at=? WHERE user_id=?",
        (amount, now(), user_id),
    )
    DB.commit()


def get_job_cost() -> float:
    return JOB_COST


def get_worker_reward() -> float:
    return WORKER_REWARD
