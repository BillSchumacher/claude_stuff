"""Run claude -p with and without plugins, capture output."""

import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from src.config import RunResult, ROOT


def resolve_plugin_path(plugin_name: str) -> Path:
    """Resolve a plugin name to its absolute directory path."""
    return (ROOT / "plugins" / plugin_name).resolve()


def build_command(
    prompt: str,
    *,
    plugin_dirs: list[Path] | None = None,
    model: str = "sonnet",
    max_budget_usd: float = 0.5,
) -> list[str]:
    """Build the claude CLI command.

    plugin_dirs=None produces a baseline run (--disable-slash-commands).
    plugin_dirs=[...] loads each plugin via --plugin-dir for skill auto-invocation.
    Uses stream-json output to capture full message history including tool calls.
    """
    cmd = [
        "claude",
        "-p",
        "--verbose",
        "--output-format", "stream-json",
        "--dangerously-skip-permissions",
        "--model", model,
        "--max-budget-usd", str(max_budget_usd),
    ]
    if not plugin_dirs:
        cmd.append("--disable-slash-commands")
    else:
        for plugin_dir in plugin_dirs:
            cmd.extend(["--plugin-dir", str(plugin_dir)])
    cmd.append(prompt)
    return cmd


def parse_stream(stdout: str) -> tuple[str, list[dict]]:
    """Parse stream-json output into (final_result_text, all_messages)."""
    messages = []
    result_text = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            messages.append(msg)
            if msg.get("type") == "result":
                result_text = msg.get("result", "")
                if msg.get("is_error"):
                    detail = msg.get("result", stdout[:500])
                    raise RuntimeError(
                        f"claude returned error: {detail}"
                    )
        except json.JSONDecodeError:
            continue
    return result_text, messages


def _exec(
    cmd: list[str],
    *,
    timeout_seconds: int = 300,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and return the result."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        cwd=cwd,
    )


def run_claude(
    cmd: list[str],
    *,
    timeout_seconds: int = 300,
    cwd: str | None = None,
) -> tuple[str, list[dict]]:
    """Execute a claude command with stream-json output. Returns (response_text, messages)."""
    result = _exec(cmd, timeout_seconds=timeout_seconds, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(
            f"claude exited with code {result.returncode}: {result.stderr or result.stdout[:500]}"
        )
    return parse_stream(result.stdout)


def run_claude_json(cmd: list[str], *, timeout_seconds: int = 300) -> str:
    """Execute a claude command with json output. Returns response text only."""
    result = _exec(cmd, timeout_seconds=timeout_seconds)
    try:
        parsed = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        parsed = {}
    if result.returncode != 0 or parsed.get("is_error"):
        detail = parsed.get("result", result.stderr or result.stdout)
        raise RuntimeError(
            f"claude exited with code {result.returncode}: {detail}"
        )
    return parsed.get("result", result.stdout)


def _make_workdir(case_id: str, variant: str) -> str:
    """Create a fresh isolated working directory for a variant run."""
    workdir = Path(tempfile.gettempdir()) / "skill_eval" / f"{case_id}_{variant}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    return str(workdir)


def run_case(
    prompt: str,
    plugins: list[str],
    case_id: str,
    *,
    model: str = "sonnet",
    max_budget_usd: float = 0.5,
    timeout_seconds: int = 300,
) -> tuple[RunResult, RunResult]:
    """Run a single test case with and without the plugins in isolated working dirs.

    Returns (with_skill_result, baseline_result).
    """
    now = datetime.now(timezone.utc).isoformat()
    plugin_dirs = [resolve_plugin_path(name) for name in plugins]

    baseline_workdir = _make_workdir(case_id, "baseline")
    baseline_cmd = build_command(
        prompt, model=model, max_budget_usd=max_budget_usd,
    )
    baseline_output, baseline_msgs = run_claude(
        baseline_cmd, timeout_seconds=timeout_seconds, cwd=baseline_workdir,
    )
    baseline = RunResult(
        case_id=case_id, variant="baseline",
        raw_output=baseline_output, model=model, timestamp=now,
        messages=baseline_msgs,
    )

    skill_workdir = _make_workdir(case_id, "with_skill")
    skill_cmd = build_command(
        prompt, plugin_dirs=plugin_dirs, model=model, max_budget_usd=max_budget_usd,
    )
    skill_output, skill_msgs = run_claude(
        skill_cmd, timeout_seconds=timeout_seconds, cwd=skill_workdir,
    )
    with_skill = RunResult(
        case_id=case_id, variant="with_skill",
        raw_output=skill_output, model=model, timestamp=now,
        messages=skill_msgs,
    )

    return with_skill, baseline


def run_cases(
    cases: Iterator[tuple[str, list[str], str]],
    *,
    model: str = "sonnet",
    max_budget_usd: float = 0.5,
) -> Iterator[tuple[RunResult, RunResult]]:
    """Iterate over (prompt, plugins, case_id) tuples, yielding result pairs."""
    for prompt, plugins, case_id in cases:
        yield run_case(
            prompt, plugins, case_id,
            model=model, max_budget_usd=max_budget_usd,
        )
