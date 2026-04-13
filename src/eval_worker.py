"""Standalone eval worker process. Survives server restarts.

Usage: python -m src.eval_worker <run_id> <cases_pattern> <model> <budget> [--model-override]
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from src.config import EVALS_DIR, ROOT
from src import results


def _normalize_path(path: str) -> str:
    """Strip temp dir prefix from file paths for cleaner display."""
    import re
    path = path.replace("\\", "/")
    match = re.search(r"skill_eval/[^/]+/(.*)", path)
    return match.group(1) if match else path.rsplit("/", 1)[-1]


def _tool_summary(tool_name: str, tool_input: dict) -> str:
    """Build a human-readable summary of a tool call."""
    if tool_name == "Write":
        path = _normalize_path(tool_input.get("file_path", ""))
        content = tool_input.get("content", "")
        lines = content.count("\n") + 1
        return f"{path} ({lines} lines)"
    if tool_name == "Edit":
        path = _normalize_path(tool_input.get("file_path", ""))
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        return f"{path} ({len(old.splitlines())} lines → {len(new.splitlines())} lines)"
    if tool_name == "Read":
        path = _normalize_path(tool_input.get("file_path", ""))
        return path
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return cmd[:200]
    if tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"{pattern}" + (f" in {_normalize_path(path)}" if path else "")
    if tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        return f"/{pattern}/"
    if tool_name == "Skill":
        skill = tool_input.get("skill", "")
        return skill
    # Generic fallback — show first key=value pairs
    parts = [f"{k}={str(v)[:50]}" for k, v in list(tool_input.items())[:3]]
    return ", ".join(parts) if parts else ""


def _should_cancel(run_id: str) -> bool:
    status = results.get_run_status(run_id)
    return status is not None and status.get("status") == "cancelling"


def main(run_id: str, cases_pattern: str, model: str, budget: float,
         model_override: bool = False) -> int:
    # Import here to avoid heavy imports at module level
    from src.cli import load_case, run_eval
    from src.runner import setup_child_cleanup

    # Ensure all subprocess descendants die when this worker exits
    setup_child_cleanup()

    glob = cases_pattern or "*.toml"
    case_paths = sorted(EVALS_DIR.glob(glob))

    started_at = datetime.now(timezone.utc).isoformat()
    results.create_run(
        run_id, started_at,
        status="running",
        total_cases=len(case_paths),
        pid=None,
    )
    # Update PID now that we have it
    import os
    results.update_run_status(run_id, status="running")
    # Store PID via direct SQL since update_run_status doesn't have pid param
    with results._get_db() as db:
        db.execute("UPDATE runs SET pid = ? WHERE run_id = ?", (os.getpid(), run_id))

    results.emit_event(run_id, "run_start", {
        "run_id": run_id, "total": len(case_paths),
    })

    for i, case_path in enumerate(case_paths):
        if _should_cancel(run_id):
            results.update_run_status(run_id, status="cancelled")
            results.emit_event(run_id, "status", {"status": "cancelled"})
            return 0

        case_name = case_path.stem
        results.update_run_status(run_id, current_case=case_name)
        results.emit_event(run_id, "case_start", {"case": case_name, "index": i})

        def _emit_stream_msg(phase: str, msg: dict) -> None:
            """Emit assistant text / tool calls for live viewing."""
            msg_type = msg.get("type", "")
            if msg_type == "assistant":
                contents = msg.get("message", {}).get("content", [])
                for c in contents:
                    if c.get("type") == "text" and c.get("text", "").strip():
                        results.emit_event(run_id, "message", {
                            "case": case_name,
                            "variant": phase,
                            "type": "text",
                            "text": c["text"][:1000],
                        })
                    elif c.get("type") == "tool_use":
                        tool_name = c.get("name", "")
                        tool_input = c.get("input", {})
                        summary = _tool_summary(tool_name, tool_input)
                        results.emit_event(run_id, "message", {
                            "case": case_name,
                            "variant": phase,
                            "type": "tool_use",
                            "tool": tool_name,
                            "summary": summary,
                        })

        def _on_message(variant: str, msg: dict) -> None:
            """Agent callback — variant is 'baseline' or 'with_skill'."""
            _emit_stream_msg(variant, msg)

        def _on_judge_message(phase: str, msg: dict) -> None:
            """Judge callback — phase is 'score:baseline', 'score:with_skill', or 'diff'."""
            _emit_stream_msg(f"judge({phase})", msg)

        try:
            result = run_eval(
                case_path, run_id,
                model=model, model_override=model_override,
                max_budget_usd=budget,
                on_message=_on_message,
                on_judge_message=_on_judge_message,
            )
            s = result["summary"]
            results.emit_event(run_id, "case_done", {
                "case": case_name,
                "baseline_score": s["baseline_score"],
                "skill_score": s["skill_score"],
                "score_delta": s["score_delta"],
                "baseline_checks": s["baseline_checks_passed"],
                "skill_checks": s["skill_checks_passed"],
                "checks": [
                    {
                        "variant": c["variant"],
                        "name": c["check_name"],
                        "passed": c["passed"],
                        "detail": (c.get("detail") or "")[:200],
                    }
                    for c in result["checks"]
                ],
            })
        except Exception as e:
            results.emit_event(run_id, "case_error", {
                "case": case_name, "error": str(e),
            })

        results.update_run_status(run_id, completed_cases=i + 1)
        results.emit_event(run_id, "progress", {
            "completed": i + 1, "total": len(case_paths),
        })

    results.update_run_status(
        run_id, status="completed", current_case=None,
    )
    results.emit_event(run_id, "status", {
        "status": "completed", "run_id": run_id,
    })
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python -m src.eval_worker <run_id> <pattern> <model> <budget> [--model-override]")
        sys.exit(1)
    try:
        override = "--model-override" in sys.argv
        code = main(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]),
                     model_override=override)
    except Exception as e:
        # Update DB on crash
        run_id = sys.argv[1]
        results.update_run_status(run_id, status="failed", error=str(e))
        results.emit_event(run_id, "status", {
            "status": "failed", "error": str(e),
        })
        raise
    sys.exit(code)
