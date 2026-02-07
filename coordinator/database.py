"""
Grid-X Coordinator - SQLite database operations with authentication support.
"""

import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

DB_PATH = os.getenv("GRIDX_DB_PATH", "gridx.db")


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# Module-level connection (same as original; for multi-threaded use consider connection per request)
_conn: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = db_connect()
    return _conn


def now() -> float:
    return time.time()


def db_init() -> None:
    """Create tables if they do not exist."""
    DB = get_db()
    # Jobs table
    DB.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            code TEXT,
            language TEXT,
            status TEXT,
            worker_id TEXT,
            created_at REAL,
            completed_at REAL,
            stdout TEXT,
            stderr TEXT
        );
    """)
    # Workers table: owner_id = user who gets credits when jobs run here
    DB.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id TEXT PRIMARY KEY,
            ip TEXT,
            cpu_cores INT,
            gpu_count INT,
            status TEXT,
            last_heartbeat REAL,
            owner_id TEXT,
            auth_token TEXT
        );
    """)
    # User credentials table for authentication
    DB.execute("""
        CREATE TABLE IF NOT EXISTS user_auth (
            user_id TEXT PRIMARY KEY,
            auth_token TEXT NOT NULL,
            created_at REAL,
            last_login REAL
        );
    """)
    # User credits: tokens decrease when using compute, increase when your compute is used
    DB.execute("""
        CREATE TABLE IF NOT EXISTS user_credits (
            user_id TEXT PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0,
            updated_at REAL
        );
    """)
    
    # Migrations: add missing columns to existing tables
    try:
        # Add owner_id to workers if missing
        cur = DB.execute("PRAGMA table_info(workers)")
        cols = [r[1] for r in cur.fetchall()]
        if "owner_id" not in cols:
            DB.execute("ALTER TABLE workers ADD COLUMN owner_id TEXT")
        if "auth_token" not in cols:
            DB.execute("ALTER TABLE workers ADD COLUMN auth_token TEXT")
    except Exception:
        pass
    
    DB.commit()


# ---------- Authentication ----------


def db_register_user(user_id: str, auth_token: str) -> None:
    """Register or update user authentication."""
    DB = get_db()
    DB.execute(
        """
        INSERT INTO user_auth(user_id, auth_token, created_at, last_login)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            auth_token=excluded.auth_token,
            last_login=excluded.last_login
        """,
        (user_id, auth_token, now(), now()),
    )
    DB.commit()


def db_verify_user_auth(user_id: str, auth_token: str) -> bool:
    """Verify user credentials."""
    row = get_db().execute(
        "SELECT auth_token FROM user_auth WHERE user_id=?", (user_id,)
    ).fetchone()
    
    if not row:
        return False
    
    return row['auth_token'] == auth_token


def db_verify_worker_auth(worker_id: str, owner_id: str, auth_token: str) -> bool:
    """Verify worker belongs to user with correct credentials."""
    row = get_db().execute(
        "SELECT owner_id, auth_token FROM workers WHERE id=?", (worker_id,)
    ).fetchone()
    
    if not row:
        return False
    
    # Verify both owner and auth match
    return row['owner_id'] == owner_id and row['auth_token'] == auth_token


def db_get_worker_by_auth(owner_id: str, auth_token: str) -> Optional[Dict[str, Any]]:
    """Get worker by owner and auth token."""
    row = get_db().execute(
        "SELECT * FROM workers WHERE owner_id=? AND auth_token=? ORDER BY last_heartbeat DESC LIMIT 1",
        (owner_id, auth_token)
    ).fetchone()
    return dict(row) if row else None


# ---------- Workers ----------


def db_upsert_worker(
    worker_id: str,
    ip: str,
    caps: Dict[str, Any],
    status: str,
    owner_id: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> None:
    DB = get_db()
    cpu_cores = int(caps.get("cpu_cores") or 0)
    gpu_count = int(1 if caps.get("gpu") else 0)
    
    # Register user auth if provided
    if owner_id and auth_token:
        db_register_user(owner_id, auth_token)
    
    DB.execute(
        """
        INSERT INTO workers(id, ip, cpu_cores, gpu_count, status, last_heartbeat, owner_id, auth_token)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            ip=excluded.ip,
            cpu_cores=excluded.cpu_cores,
            gpu_count=excluded.gpu_count,
            status=excluded.status,
            last_heartbeat=excluded.last_heartbeat,
            owner_id=excluded.owner_id,
            auth_token=excluded.auth_token
        """,
        (worker_id, ip, cpu_cores, gpu_count, status, now(), owner_id or "", auth_token or ""),
    )
    DB.commit()


def db_set_worker_status(worker_id: str, status: str) -> None:
    get_db().execute(
        "UPDATE workers SET status=?, last_heartbeat=? WHERE id=?",
        (status, now(), worker_id),
    )
    get_db().commit()


def db_get_worker(worker_id: str) -> Optional[Dict[str, Any]]:
    row = get_db().execute("SELECT * FROM workers WHERE id=?", (worker_id,)).fetchone()
    return dict(row) if row else None


def db_list_workers() -> List[Dict[str, Any]]:
    rows = get_db().execute("SELECT * FROM workers").fetchall()
    return [dict(r) for r in rows]


def db_list_workers_by_owner(owner_id: str) -> List[Dict[str, Any]]:
    """List all workers owned by a specific user."""
    rows = get_db().execute(
        "SELECT * FROM workers WHERE owner_id=?", (owner_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def db_set_worker_offline(worker_id: str) -> None:
    get_db().execute(
        "UPDATE workers SET status=?, last_heartbeat=? WHERE id=?",
        ("offline", now(), worker_id),
    )
    get_db().commit()


def db_cleanup_duplicate_workers(owner_id: str, auth_token: str, keep_worker_id: str) -> None:
    """Remove duplicate workers for a user, keeping only the specified one."""
    get_db().execute(
        """
        DELETE FROM workers 
        WHERE owner_id=? AND auth_token=? AND id!=? AND status='offline'
        """,
        (owner_id, auth_token, keep_worker_id)
    )
    get_db().commit()


# ---------- Jobs ----------


def db_create_job(
    job_id: str,
    user_id: str,
    code: str,
    language: str,
    limits: Optional[Dict[str, Any]] = None,
) -> None:
    get_db().execute(
        """
        INSERT INTO jobs(id, user_id, code, language, status, worker_id, created_at, completed_at, stdout, stderr)
        VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        (job_id, user_id, code, language, "queued", None, now(), None, "", ""),
    )
    get_db().commit()


def db_set_job_assigned(job_id: str, worker_id: str) -> None:
    get_db().execute(
        "UPDATE jobs SET status=?, worker_id=? WHERE id=?",
        ("assigned", worker_id, job_id),
    )
    get_db().commit()


def db_set_job_running(job_id: str) -> None:
    get_db().execute("UPDATE jobs SET status=? WHERE id=?", ("running", job_id))
    get_db().commit()


def db_set_job_completed(
    job_id: str, stdout: str, stderr: str, exit_code: int
) -> None:
    status = "completed" if exit_code == 0 else "failed"
    get_db().execute(
        "UPDATE jobs SET status=?, completed_at=?, stdout=?, stderr=? WHERE id=?",
        (status, now(), stdout, stderr, job_id),
    )
    get_db().commit()


def db_get_job(job_id: str) -> Optional[Dict[str, Any]]:
    row = get_db().execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None


# Initialize on import
db_init()
