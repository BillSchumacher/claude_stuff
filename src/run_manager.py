"""Manages eval runs as independent subprocesses with DB-persisted state.

The eval worker runs in its own process (survives server restarts).
Status and events are stored in SQLite, polled by the server for SSE.
"""

import subprocess
import sys
from datetime import datetime, timezone

from src.config import ROOT, EVALS_DIR
from src import results


def get_active_runs() -> list[dict]:
    """Get all currently active runs from DB. Cleans up stale/dead ones."""
    actives = results.get_all_active_runs()
    live = []
    for active in actives:
        if not active.get("pid"):
            results.update_run_status(active["run_id"], status="failed", error="Stale run (no PID)")
            continue
        if not _pid_alive(active["pid"]):
            results.update_run_status(
                active["run_id"], status="failed",
                error="Worker process died unexpectedly",
            )
            continue
        live.append(active)
    return live


def get_status() -> dict:
    """Get status of the most recent active run (for SSE/status bar)."""
    actives = get_active_runs()
    if actives:
        # Return the most recently started one for the status bar
        active = actives[-1]
        return {
            "run_id": active["run_id"],
            "status": active["status"],
            "current_case": active["current_case"],
            "total_cases": active["total_cases"],
            "completed_cases": active["completed_cases"],
            "error": active.get("error"),
            "active_count": len(actives),
        }
    return {
        "run_id": None,
        "status": "idle",
        "current_case": None,
        "total_cases": 0,
        "completed_cases": 0,
        "error": None,
        "active_count": 0,
    }


def cancel(run_id: str | None = None) -> bool:
    """Request cancellation. If run_id given, cancel that run; otherwise cancel all.

    Sets the cancel flag in the DB AND force-kills the worker process tree
    so in-progress subprocesses (claude, dev servers, etc.) are terminated.
    """
    if run_id:
        runs = [results.get_run_status(run_id)]
        runs = [r for r in runs if r]
    else:
        runs = get_active_runs()

    cancelled = False
    for run in runs:
        rid = run["run_id"]
        pid = run.get("pid")
        if results.request_cancel(rid):
            cancelled = True
        if pid:
            _kill_process_tree(pid)
            results.update_run_status(rid, status="cancelled")
            results.emit_event(rid, "status", {"status": "cancelled"})
    return cancelled


def _kill_process_tree(pid: int) -> None:
    """Forcefully terminate a process and all its descendants."""
    if sys.platform == "win32":
        # taskkill /T kills the process tree
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass
    else:
        import os
        import signal
        try:
            # Kill the whole process group (we used start_new_session)
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def start_run(
    cases_pattern: str | None = None,
    model: str = "sonnet",
    max_budget_usd: float = 0.5,
    model_override: bool = False,
) -> str | None:
    """Spawn an eval worker subprocess. Returns run_id or None if no cases match.

    Multiple runs can execute concurrently.
    """
    glob = cases_pattern or "*.toml"
    case_paths = sorted(EVALS_DIR.glob(glob))
    if not case_paths:
        return None

    # Include model in run_id to avoid collisions between concurrent model runs
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + f"_{model}"

    cmd = [
        sys.executable, "-m", "src.eval_worker",
        run_id, glob, model, str(max_budget_usd),
    ]
    if model_override:
        cmd.append("--model-override")

    subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        if sys.platform == "win32" else 0,
        start_new_session=True if sys.platform != "win32" else False,
    )

    return run_id


def get_events_since(run_id: str, after_id: int = 0) -> list[dict]:
    """Poll DB for new events since a given event ID."""
    return results.get_events_since(run_id, after_id)


def _pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        import os
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
