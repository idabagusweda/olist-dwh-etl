"""
dashboard/scheduler_engine.py — Lightweight ETL scheduler engine.

Uses APScheduler (BackgroundScheduler) for non-blocking execution.
Runs the master ETL pipeline (scripts/06_run_etl_pipeline.py) as a
subprocess to avoid import side-effects and ensure isolation.

State is persisted in Streamlit session_state and in the etl_log table
of the DWH database.
"""

import os
import sys
import time
import sqlite3
import subprocess
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "olist_dwh.db")
ETL_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "06_run_etl_pipeline.py")
PYTHON_EXE = sys.executable  # use the same Python as the dashboard

# ---------------------------------------------------------------------------
# Data classes for scheduler state
# ---------------------------------------------------------------------------

@dataclass
class ETLRunResult:
    """Result of a single ETL execution."""
    run_id: str = ""
    trigger: str = "manual"          # "manual" | "scheduled"
    status: str = "pending"          # "pending" | "running" | "success" | "error"
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    error_message: str = ""
    return_code: int = -1


# ---------------------------------------------------------------------------
# ETL execution log table
# ---------------------------------------------------------------------------

def _ensure_log_table():
    """Create the etl_log table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS etl_log (
            run_id          TEXT PRIMARY KEY,
            trigger         TEXT NOT NULL DEFAULT 'manual',
            status          TEXT NOT NULL DEFAULT 'pending',
            started_at      TEXT,
            finished_at     TEXT,
            duration_seconds REAL DEFAULT 0,
            stdout          TEXT DEFAULT '',
            stderr          TEXT DEFAULT '',
            error_message   TEXT DEFAULT '',
            return_code     INTEGER DEFAULT -1
        )
    """)
    conn.commit()
    conn.close()


def save_run_result(result: ETLRunResult):
    """Insert or update an ETL run result in the log table."""
    _ensure_log_table()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("""
        INSERT OR REPLACE INTO etl_log
            (run_id, trigger, status, started_at, finished_at,
             duration_seconds, stdout, stderr, error_message, return_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result.run_id, result.trigger, result.status,
        result.started_at, result.finished_at,
        result.duration_seconds, result.stdout, result.stderr,
        result.error_message, result.return_code,
    ))
    conn.commit()
    conn.close()


def get_run_history(limit: int = 50) -> list[dict]:
    """Retrieve recent ETL run history."""
    _ensure_log_table()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM etl_log ORDER BY started_at DESC LIMIT ?",
        (limit,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_last_successful_run() -> dict | None:
    """Return the most recent successful run, or None."""
    _ensure_log_table()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM etl_log WHERE status='success' ORDER BY finished_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Lock to prevent overlapping ETL runs
# ---------------------------------------------------------------------------
_etl_lock = threading.Lock()


def is_etl_running() -> bool:
    """Check if an ETL execution is currently in progress."""
    return _etl_lock.locked()


def run_etl_pipeline(trigger: str = "manual") -> ETLRunResult:
    """
    Execute the master ETL pipeline as a subprocess.
    
    Returns an ETLRunResult. Blocks until the subprocess finishes.
    Thread-safe: only one execution at a time is allowed.
    """
    if not _etl_lock.acquire(blocking=False):
        return ETLRunResult(
            run_id="",
            trigger=trigger,
            status="error",
            error_message="Another ETL execution is already in progress.",
        )

    result = ETLRunResult(
        run_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
        trigger=trigger,
        status="running",
        started_at=datetime.now().isoformat(),
    )

    try:
        # Validate that the ETL script exists
        if not os.path.exists(ETL_SCRIPT):
            result.status = "error"
            result.error_message = f"ETL script not found: {ETL_SCRIPT}"
            result.finished_at = datetime.now().isoformat()
            save_run_result(result)
            return result

        # Save initial "running" state
        save_run_result(result)

        start_time = time.time()

        # Run as subprocess for isolation
        proc = subprocess.run(
            [PYTHON_EXE, ETL_SCRIPT],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=600,  # 10-minute timeout
        )

        elapsed = time.time() - start_time
        result.duration_seconds = round(elapsed, 2)
        result.stdout = proc.stdout or ""
        result.stderr = proc.stderr or ""
        result.return_code = proc.returncode
        result.finished_at = datetime.now().isoformat()

        if proc.returncode == 0:
            result.status = "success"
        else:
            result.status = "error"
            result.error_message = (
                proc.stderr.strip()[-500:] if proc.stderr
                else f"Process exited with code {proc.returncode}"
            )

    except subprocess.TimeoutExpired:
        result.status = "error"
        result.error_message = "ETL execution timed out after 10 minutes."
        result.finished_at = datetime.now().isoformat()
    except Exception as e:
        result.status = "error"
        result.error_message = str(e)[:500]
        result.finished_at = datetime.now().isoformat()
    finally:
        save_run_result(result)
        _etl_lock.release()

    return result


# ---------------------------------------------------------------------------
# Background scheduler (APScheduler)
# ---------------------------------------------------------------------------
_scheduler = None
_scheduler_lock = threading.Lock()


def _get_interval_kwargs(interval_type: str, custom_minutes: int = 60) -> dict:
    """Convert a user-friendly interval to APScheduler kwargs."""
    mapping = {
        "Every 30 minutes": {"minutes": 30},
        "Every 1 hour": {"hours": 1},
        "Every 6 hours": {"hours": 6},
        "Every 12 hours": {"hours": 12},
        "Daily": {"days": 1},
        "Weekly": {"weeks": 1},
        "Custom (minutes)": {"minutes": max(5, custom_minutes)},
    }
    return mapping.get(interval_type, {"days": 1})


def start_scheduler(interval_type: str, custom_minutes: int = 60) -> str:
    """Start the background ETL scheduler.
    
    Returns a status message.
    """
    global _scheduler

    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            return "Scheduler is already running."

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError:
            return "APScheduler is not installed. Run: pip install apscheduler"

        _scheduler = BackgroundScheduler(daemon=True)
        interval_kwargs = _get_interval_kwargs(interval_type, custom_minutes)

        _scheduler.add_job(
            func=run_etl_pipeline,
            trigger="interval",
            kwargs={"trigger": "scheduled"},
            id="etl_pipeline",
            replace_existing=True,
            **interval_kwargs,
        )

        _scheduler.start()
        return f"Scheduler started with interval: {interval_type}"


def stop_scheduler() -> str:
    """Stop the background ETL scheduler."""
    global _scheduler

    with _scheduler_lock:
        if _scheduler is None or not _scheduler.running:
            _scheduler = None
            return "Scheduler is not running."

        _scheduler.shutdown(wait=False)
        _scheduler = None
        return "Scheduler stopped."


def get_scheduler_status() -> dict:
    """Return current scheduler status information."""
    global _scheduler

    with _scheduler_lock:
        if _scheduler is None or not _scheduler.running:
            return {
                "running": False,
                "next_run": None,
                "interval": None,
            }

        jobs = _scheduler.get_jobs()
        next_run = None
        if jobs:
            next_run = jobs[0].next_run_time

        return {
            "running": True,
            "next_run": next_run.isoformat() if next_run else None,
            "interval": str(jobs[0].trigger) if jobs else None,
        }


# Ensure the log table exists on import
_ensure_log_table()
