"""
Grid-X Coordinator - SQLite database operations.
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
    # Workers table: owner_id = user who gets credits when jobs run on this worker
    DB.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id TEXT PRIMARY KEY,
            ip TEXT,
            cpu_cores INT,
            gpu_count INT,
            status TEXT,
            last_heartbeat REAL,
            owner_id TEXT
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
    # Migration: add owner_id to workers if missing (existing DBs)
    try:
        cur = DB.execute("PRAGMA table_info(workers)")
        cols = [r[1] for r in cur.fetchall()]
        if "owner_id" not in cols:
            DB.execute("ALTER TABLE workers ADD COLUMN owner_id TEXT")
    except Exception:
        pass
    DB.commit()


# ---------- Workers ----------


def db_upsert_worker(
    worker_id: str,
    ip: str,
    caps: Dict[str, Any],
    status: str,
    owner_id: Optional[str] = None,
) -> None:
    DB = get_db()
    cpu_cores = int(caps.get("cpu_cores") or 0)
    gpu_count = int(1 if caps.get("gpu") else 0)
    DB.execute(
        """
        INSERT INTO workers(id, ip, cpu_cores, gpu_count, status, last_heartbeat, owner_id)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            ip=excluded.ip,
            cpu_cores=excluded.cpu_cores,
            gpu_count=excluded.gpu_count,
            status=excluded.status,
            last_heartbeat=excluded.last_heartbeat,
            owner_id=excluded.owner_id
        """,
        (worker_id, ip, cpu_cores, gpu_count, status, now(), owner_id or ""),
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


def db_set_worker_offline(worker_id: str) -> None:
    get_db().execute(
        "UPDATE workers SET status=?, last_heartbeat=? WHERE id=?",
        ("offline", now(), worker_id),
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
