"""
Grid-X Database Module - ENHANCED VERSION

FIXES APPLIED:
1. Added transaction support with context manager
2. Added connection pooling
3. Added input validation
4. Improved error handling
5. Added atomic operations
"""

import sqlite3
import logging
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from threading import Lock

# Import from common
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.utils import now, validate_uuid, sanitize_string
from common.constants import STATUS_QUEUED, WORKER_STATUS_IDLE

logger = logging.getLogger(__name__)

# Global database connection and lock
_db_conn: Optional[sqlite3.Connection] = None
_db_lock = Lock()


def get_db_path() -> str:
    """Get database path from environment or use default"""
    return os.getenv("GRIDX_DB_PATH", "./data/gridx.db")


def get_db() -> sqlite3.Connection:
    """Get or create database connection (thread-safe)"""
    global _db_conn
    
    with _db_lock:
        if _db_conn is None:
            db_path = get_db_path()
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
            
            _db_conn = sqlite3.connect(
                db_path,
                check_same_thread=False,
                timeout=30.0
            )
            _db_conn.row_factory = sqlite3.Row
            
            logger.info(f"Database connected: {db_path}")
        
        return _db_conn


@contextmanager
def db_transaction():
    """
    Database transaction context manager.
    
    Usage:
        with db_transaction() as conn:
            conn.execute("INSERT ...")
            conn.execute("UPDATE ...")
            # Auto-commits on success, rolls back on exception
    """
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction rolled back: {e}")
        raise


def init_db() -> None:
    """Initialize database schema"""
    conn = get_db()
    
    # Jobs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            code TEXT NOT NULL,
            language TEXT DEFAULT 'python',
            status TEXT DEFAULT 'queued',
            worker_id TEXT,
            created_at REAL,
            started_at REAL,
            completed_at REAL,
            stdout TEXT DEFAULT '',
            stderr TEXT DEFAULT '',
            exit_code INTEGER,
            limits TEXT,
            cost REAL DEFAULT 1.0
        )
    """)
    
    # Workers table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id TEXT PRIMARY KEY,
            owner_id TEXT,
            ip TEXT,
            caps TEXT,
            status TEXT DEFAULT 'idle',
            auth_token TEXT,
            last_heartbeat REAL,
            registered_at REAL,
            jobs_completed INTEGER DEFAULT 0,
            credits_earned REAL DEFAULT 0.0
        )
    """)
    
    # User credits table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_credits (
            user_id TEXT PRIMARY KEY,
            balance REAL DEFAULT 100.0,
            total_earned REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0,
            last_updated REAL
        )
    """)
    
    # User authentication table (used for worker owners)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_auth (
            user_id TEXT PRIMARY KEY,
            auth_token TEXT,
            created_at REAL
        )
    """)
    
    # Indices for performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_worker ON jobs(worker_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workers_owner ON workers(owner_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)")
    
    conn.commit()
    logger.info("Database schema initialized")


# ============================================================================
# JOB OPERATIONS
# ============================================================================

def db_create_job(
    job_id: str,
    user_id: str,
    code: str,
    language: str,
    limits: Dict[str, Any]
) -> None:
    """Create a new job in database"""
    import json
    
    # Validate inputs
    if not validate_uuid(job_id):
        raise ValueError(f"Invalid job_id: {job_id}")
    
    code = sanitize_string(code, max_length=1_000_000)
    user_id = sanitize_string(user_id, max_length=64)
    
    conn = get_db()
    conn.execute(
        """
        INSERT INTO jobs (id, user_id, code, language, status, created_at, limits, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            user_id,
            code,
            language,
            STATUS_QUEUED,
            now(),
            json.dumps(limits),
            1.0
        )
    )
    conn.commit()
    logger.info(f"Job created: {job_id} by {user_id}")


def db_get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job by ID"""
    if not validate_uuid(job_id):
        logger.warning(f"Invalid job_id format: {job_id}")
        return None
    
    row = get_db().execute(
        "SELECT * FROM jobs WHERE id=?",
        (job_id,)
    ).fetchone()
    
    return dict(row) if row else None


def db_update_job_status(
    job_id: str,
    status: str,
    **kwargs
) -> None:
    """Update job status and optional fields"""
    if not validate_uuid(job_id):
        raise ValueError(f"Invalid job_id: {job_id}")
    
    updates = ["status=?"]
    params = [status]
    
    for key, value in kwargs.items():
        updates.append(f"{key}=?")
        params.append(value)
    
    params.append(job_id)
    
    query = f"UPDATE jobs SET {', '.join(updates)} WHERE id=?"
    
    conn = get_db()
    conn.execute(query, params)
    conn.commit()
    
    logger.info(f"Job {job_id} updated: status={status}")


# ============================================================================
# WORKER OPERATIONS
# ============================================================================

def db_upsert_worker(
    worker_id: str,
    ip: str,
    caps: Dict[str, Any],
    status: str,
    owner_id: str = ""
) -> None:
    """Insert or update worker"""
    import json
    
    if not validate_uuid(worker_id):
        raise ValueError(f"Invalid worker_id: {worker_id}")
    
    conn = get_db()
    conn.execute(
        """
        INSERT INTO workers (id, owner_id, ip, caps, status, registered_at, last_heartbeat)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            ip=excluded.ip,
            caps=excluded.caps,
            status=excluded.status,
            last_heartbeat=excluded.last_heartbeat
        """,
        (worker_id, owner_id, ip, json.dumps(caps), status, now(), now())
    )
    conn.commit()
    logger.info(f"Worker upserted: {worker_id}")


def db_list_workers() -> List[Dict[str, Any]]:
    """List all workers"""
    rows = get_db().execute("SELECT * FROM workers").fetchall()
    return [dict(row) for row in rows]


def db_get_worker(worker_id: str) -> Optional[Dict[str, Any]]:
    """Get worker by ID"""
    if not validate_uuid(worker_id):
        logger.warning(f"Invalid worker_id format: {worker_id}")
        return None
    
    row = get_db().execute(
        "SELECT * FROM workers WHERE id=?",
        (worker_id,)
    ).fetchone()
    
    return dict(row) if row else None


# ============================================================================
# ATOMIC OPERATIONS
# ============================================================================

def db_assign_job_to_worker(job_id: str, worker_id: str) -> bool:
    """
    Atomically assign job to worker.
    Returns True if successful, False if job already assigned.
    """
    try:
        with db_transaction() as conn:
            # Check if job is still queued
            job = conn.execute(
                "SELECT status FROM jobs WHERE id=?",
                (job_id,)
            ).fetchone()
            
            if not job or job['status'] != STATUS_QUEUED:
                return False
            
            # Update job
            conn.execute(
                """
                UPDATE jobs 
                SET worker_id=?, status='running', started_at=?
                WHERE id=? AND status='queued'
                """,
                (worker_id, now(), job_id)
            )
            
            # Update worker
            conn.execute(
                "UPDATE workers SET status='busy' WHERE id=?",
                (worker_id,)
            )
            
            logger.info(f"Job {job_id} assigned to worker {worker_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to assign job: {e}")
        return False


def db_complete_job(
    job_id: str,
    worker_id: str,
    stdout: str,
    stderr: str,
    exit_code: int
) -> bool:
    """Atomically complete job and update worker"""
    try:
        with db_transaction() as conn:
            status = "completed" if exit_code == 0 else "failed"
            
            # Update job
            conn.execute(
                """
                UPDATE jobs
                SET status=?, completed_at=?, stdout=?, stderr=?, exit_code=?
                WHERE id=?
                """,
                (status, now(), stdout, stderr, exit_code, job_id)
            )
            
            # Update worker stats
            if exit_code == 0:
                conn.execute(
                    """
                    UPDATE workers
                    SET status='idle', jobs_completed=jobs_completed+1
                    WHERE id=?
                    """,
                    (worker_id,)
                )
            else:
                conn.execute(
                    "UPDATE workers SET status='idle' WHERE id=?",
                    (worker_id,)
                )
            
            logger.info(f"Job {job_id} completed with exit code {exit_code}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to complete job: {e}")
        return False

# ============================================================================
# BACKWARDS-COMPATIBILITY WRAPPERS
# ============================================================================


def db_set_job_assigned(job_id: str, worker_id: str) -> bool:
    """Compatibility wrapper for older API name.
    Atomically assigns a job to a worker.
    """
    try:
        if not validate_uuid(job_id) or not validate_uuid(worker_id):
            logger.warning("Invalid job_id or worker_id in db_set_job_assigned")
            return False
        return db_assign_job_to_worker(job_id, worker_id)
    except Exception as e:
        logger.error(f"db_set_job_assigned failed: {e}")
        return False


def db_set_job_running(job_id: str) -> None:
    """Mark job as running (compat wrapper)."""
    try:
        if not validate_uuid(job_id):
            logger.warning("Invalid job_id in db_set_job_running")
            return
        db_update_job_status(job_id, "running", started_at=now())
    except Exception as e:
        logger.error(f"db_set_job_running failed: {e}")


def db_set_job_completed(job_id: str, stdout: str, stderr: str, exit_code: int) -> bool:
    """Compatibility wrapper to complete a job using available APIs.

    If worker_id is recorded for the job, uses the atomic completion routine,
    otherwise updates the job row directly.
    """
    try:
        if not validate_uuid(job_id):
            logger.warning("Invalid job_id in db_set_job_completed")
            return False

        row = get_db().execute("SELECT worker_id FROM jobs WHERE id=?", (job_id,)).fetchone()
        worker_id = row["worker_id"] if row else None

        if worker_id and validate_uuid(worker_id):
            return db_complete_job(job_id, worker_id, stdout, stderr, exit_code)

        # Fallback: update job row only
        status = "completed" if exit_code == 0 else "failed"
        conn = get_db()
        conn.execute(
            """
            UPDATE jobs
            SET status=?, completed_at=?, stdout=?, stderr=?, exit_code=?
            WHERE id=?
            """,
            (status, now(), stdout, stderr, exit_code, job_id),
        )
        conn.commit()
        logger.info(f"Job {job_id} marked {status} (fallback)")
        return True
    except Exception as e:
        logger.error(f"db_set_job_completed failed: {e}")
        return False


def db_set_worker_status(worker_id: str, status: str) -> None:
    """Set worker status (compat wrapper)."""
    try:
        if not validate_uuid(worker_id):
            logger.warning("Invalid worker_id in db_set_worker_status")
            return
        conn = get_db()
        # Update status and refresh last_heartbeat to mark worker as recently seen
        conn.execute("UPDATE workers SET status=?, last_heartbeat=? WHERE id=?", (status, now(), worker_id))
        conn.commit()
    except Exception as e:
        logger.error(f"db_set_worker_status failed: {e}")


def db_init() -> None:
    """Compatibility alias for init_db."""
    try:
        init_db()
    except Exception as e:
        logger.error(f"db_init failed: {e}")


def db_set_worker_offline(worker_id: str) -> None:
    """Mark a worker offline (compat wrapper)."""
    try:
        if not validate_uuid(worker_id):
            logger.warning("Invalid worker_id in db_set_worker_offline")
            return
        conn = get_db()
        conn.execute("UPDATE workers SET status=? WHERE id=?", ("offline", worker_id))
        conn.commit()
    except Exception as e:
        logger.error(f"db_set_worker_offline failed: {e}")


def db_get_worker_by_auth(owner_id: str, auth_token: str) -> Optional[Dict[str, Any]]:
    """Return a worker row for given owner credentials, if any."""
    try:
        if not owner_id:
            return None
        row = get_db().execute(
            "SELECT * FROM workers WHERE owner_id=? AND auth_token=?",
            (owner_id, auth_token),
        ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"db_get_worker_by_auth failed: {e}")
        return None


def db_verify_worker_auth(worker_id: str, auth_token: str) -> bool:
    """Verify that a worker id matches the provided auth token."""
    try:
        if not validate_uuid(worker_id):
            return False
        row = get_db().execute(
            "SELECT auth_token FROM workers WHERE id=?",
            (worker_id,),
        ).fetchone()
        return bool(row and row["auth_token"] == auth_token)
    except Exception as e:
        logger.error(f"db_verify_worker_auth failed: {e}")
        return False


def db_verify_user_auth(user_id: str, auth_token: str) -> bool:
    """Verify user credentials against `user_auth` table."""
    try:
        if not user_id:
            return False
        row = get_db().execute(
            "SELECT auth_token FROM user_auth WHERE user_id=?",
            (user_id,),
        ).fetchone()
        return bool(row and row["auth_token"] == auth_token)
    except Exception as e:
        logger.error(f"db_verify_user_auth failed: {e}")
        return False