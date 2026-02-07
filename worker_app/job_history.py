"""
Local job history storage - persists job info for offline viewing.
Stored in ~/.gridx/job_history_{user_id}.json
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


def _get_history_path(user_id: str) -> Path:
    """Get path to job history file for user."""
    config_dir = Path.home() / ".gridx"
    config_dir.mkdir(parents=True, exist_ok=True)
    safe_user = "".join(c for c in user_id if c.isalnum() or c in "._-")[:64] or "default"
    return config_dir / f"job_history_{safe_user}.json"


def load_job_history(user_id: str) -> List[Dict[str, Any]]:
    """Load job history from disk. Returns list of job records, most recent first."""
    path = _get_history_path(user_id)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_job_history(user_id: str, jobs: List[Dict[str, Any]]) -> None:
    """Save job history to disk. Keeps last 100 jobs."""
    path = _get_history_path(user_id)
    jobs = jobs[:100]
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2)
    except Exception:
        pass


def add_job_to_history(user_id: str, job_id: str, language: str = "python", code_preview: str = "") -> None:
    """Add or update a job in history (e.g. when submitted)."""
    jobs = load_job_history(user_id)
    now = time.time()
    # Remove existing if present (to re-add at top)
    jobs = [j for j in jobs if j.get("job_id") != job_id and j.get("id") != job_id]
    jobs.insert(0, {
        "job_id": job_id,
        "id": job_id,
        "status": "queued",
        "language": language,
        "code_preview": (code_preview or "")[:80],
        "created_at": now,
        "stdout": "",
        "stderr": "",
    })
    save_job_history(user_id, jobs)


def update_job_in_history(user_id: str, job_data: Dict[str, Any]) -> None:
    """Update a job record with fetched data from coordinator."""
    job_id = job_data.get("id") or job_data.get("job_id")
    if not job_id:
        return
    jobs = load_job_history(user_id)
    for i, j in enumerate(jobs):
        if j.get("job_id") == job_id or j.get("id") == job_id:
            merged = {**j, **job_data}
            merged["job_id"] = job_id
            merged["id"] = job_id
            jobs[i] = merged
            save_job_history(user_id, jobs)
            return
    # Not found - add as new
    record = {
        "job_id": job_id,
        "id": job_id,
        "status": job_data.get("status", "unknown"),
        "language": job_data.get("language", "python"),
        "code_preview": (job_data.get("code", "") or "")[:80],
        "created_at": job_data.get("created_at", time.time()),
        "stdout": job_data.get("stdout", ""),
        "stderr": job_data.get("stderr", ""),
        "exit_code": job_data.get("exit_code"),
    }
    jobs.insert(0, record)
    save_job_history(user_id, jobs)


def get_merged_job_history(user_id: str, coordinator_jobs: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
    """
    Merge local history with coordinator jobs. Coordinator data takes precedence.
    Returns unified list, most recent first.
    """
    local = load_job_history(user_id)
    by_id = {}
    for j in local:
        mid = j.get("job_id") or j.get("id")
        if mid:
            by_id[mid] = j.copy()
    if coordinator_jobs:
        for j in coordinator_jobs:
            mid = j.get("id") or j.get("job_id")
            if mid:
                by_id[mid] = {**by_id.get(mid, {}), **j, "job_id": mid, "id": mid}
    out = list(by_id.values())
    out.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
    return out[:100]
