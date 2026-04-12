"""Run claude -p with and without plugins, capture output."""

import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from src.config import RunResult, ROOT

# Settings JSON to isolate eval runs from user config.
# Disables auto-memory; excludes all CLAUDE.md files so neither global
# preferences nor project instructions leak into baseline or skill runs.
_ISOLATION_SETTINGS = json.dumps({
    "autoMemoryEnabled": False,
    "claudeMdExcludes": ["C:/**", "/**"],
})


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
        "--verbose",
        "--output-format", "stream-json",
        "--dangerously-skip-permissions",
        "--permission-mode", "bypassPermissions",
        "--model", model,
        "--max-budget-usd", str(max_budget_usd),
        "--settings", _ISOLATION_SETTINGS,
    ]
    if not plugin_dirs:
        cmd.append("--disable-slash-commands")
    else:
        for plugin_dir in plugin_dirs:
            cmd.extend(["--plugin-dir", str(plugin_dir)])
    cmd.extend(["-p", prompt])
    return cmd


def parse_stream(stdout: str) -> tuple[str, list[dict]]:
    """Parse stream-json output into (final_result_text, all_messages).

    Budget exhaustion (error_max_budget_usd) is treated as a soft stop —
    the agent produced output before running out.  Other errors are raised.
    """
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
                    subtype = msg.get("subtype", "")
                    if subtype == "error_max_budget_usd":
                        # Budget exhaustion — agent did useful work, keep going
                        continue
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
    stdin_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and return the result.

    Forces UTF-8 decoding of stdout/stderr. Without this, Windows defaults to
    cp1252 and crashes on UTF-8 bytes emitted by claude (e.g., smart quotes,
    emoji, non-ASCII names).

    stdin_text: if provided, pipe this text to the process's stdin. Used by the
    scorer and differ to avoid exceeding Windows command-line length limits when
    passing large prompts.
    """
    env = {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
    return subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        cwd=cwd,
        env=env,
    )


def run_claude(
    cmd: list[str],
    *,
    timeout_seconds: int = 300,
    cwd: str | None = None,
    on_message: Callable[[dict], None] | None = None,
) -> tuple[str, list[dict]]:
    """Execute a claude command with stream-json output. Returns (response_text, messages).

    on_message: if provided, called with each parsed JSON message as it arrives
    (enables live streaming to the UI). Falls back to batch mode if not set.

    Retries once on non-zero exit (transient init failures, API errors).
    """
    if on_message:
        return _run_claude_streaming(
            cmd, timeout_seconds=timeout_seconds, cwd=cwd,
            on_message=on_message,
        )

    for attempt in range(2):
        result = _exec(cmd, timeout_seconds=timeout_seconds, cwd=cwd)
        if result.returncode == 0:
            break
        if attempt == 0:
            time.sleep(5)
    if result.returncode != 0:
        raise RuntimeError(
            f"claude exited with code {result.returncode}: {result.stderr or result.stdout[:500]}"
        )
    return parse_stream(result.stdout)


def _run_claude_streaming(
    cmd: list[str],
    *,
    timeout_seconds: int = 300,
    cwd: str | None = None,
    on_message: Callable[[dict], None],
) -> tuple[str, list[dict]]:
    """Run claude and stream each JSON message as it arrives."""
    env = {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
    )

    messages = []
    result_text = ""
    deadline = time.time() + timeout_seconds

    try:
        for raw_line in proc.stdout:
            if time.time() > deadline:
                proc.kill()
                raise TimeoutError(f"claude timed out after {timeout_seconds}s")

            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            messages.append(msg)
            on_message(msg)

            if msg.get("type") == "result":
                result_text = msg.get("result", "")
                if msg.get("is_error"):
                    subtype = msg.get("subtype", "")
                    if subtype == "error_max_budget_usd":
                        continue
                    detail = msg.get("result", "")[:500]
                    raise RuntimeError(f"claude returned error: {detail}")
    finally:
        proc.wait(timeout=10)

    if proc.returncode and proc.returncode != 0:
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        raise RuntimeError(
            f"claude exited with code {proc.returncode}: {stderr[:500]}"
        )

    return result_text, messages


def run_claude_json(
    cmd: list[str],
    *,
    timeout_seconds: int = 300,
    stdin_text: str | None = None,
) -> str:
    """Execute a claude command with json output. Returns response text only.

    stdin_text: if provided, pipe as stdin (for large prompts that exceed
    Windows command-line limits).
    """
    result = _exec(cmd, timeout_seconds=timeout_seconds, stdin_text=stdin_text)
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


def _make_workdir(
    case_id: str,
    variant: str,
    *,
    fixture_dir: Path | None = None,
) -> str:
    """Create a fresh isolated working directory for a variant run.

    If fixture_dir is provided, copies its contents into the workdir and
    initialises a git repo so the agent's changes can be diffed.
    """
    workdir = Path(tempfile.gettempdir()) / "skill_eval" / f"{case_id}_{variant}"
    if workdir.exists():
        try:
            shutil.rmtree(workdir)
        except PermissionError:
            # Windows file lock from a prior claude child process — use alternate dir
            workdir = workdir.with_name(f"{case_id}_{variant}_{int(time.time())}")
    workdir.mkdir(parents=True, exist_ok=True)

    if fixture_dir and fixture_dir.is_dir():
        shutil.copytree(fixture_dir, workdir, dirs_exist_ok=True)
        # Init git so the agent's edits produce a clean diff
        subprocess.run(
            ["git", "init"], cwd=str(workdir),
            capture_output=True, timeout=30,
        )
        subprocess.run(
            ["git", "add", "-A"], cwd=str(workdir),
            capture_output=True, timeout=30,
        )
        subprocess.run(
            ["git", "-c", "user.name=eval", "-c", "user.email=eval@test",
             "commit", "-m", "initial fixture"],
            cwd=str(workdir), capture_output=True, timeout=30,
        )

    return str(workdir)


def run_case(
    prompt: str,
    plugins: list[str],
    case_id: str,
    *,
    model: str = "sonnet",
    max_budget_usd: float = 0.5,
    timeout_seconds: int = 300,
    fixture_dir: Path | None = None,
    on_message: Callable[[str, dict], None] | None = None,
) -> tuple[RunResult, RunResult]:
    """Run a single test case with and without the plugins in isolated working dirs.

    If fixture_dir is provided, its contents are copied into each workdir and
    a git repo is initialised so the agent's changes can be diffed.

    on_message: if provided, called with (variant, msg) for each streamed JSON message.

    Returns (with_skill_result, baseline_result).
    """
    now = datetime.now(timezone.utc).isoformat()
    plugin_dirs = [resolve_plugin_path(name) for name in plugins]

    baseline_workdir = _make_workdir(case_id, "baseline", fixture_dir=fixture_dir)
    baseline_cmd = build_command(
        prompt, model=model, max_budget_usd=max_budget_usd,
    )
    baseline_cb = (lambda msg: on_message("baseline", msg)) if on_message else None
    baseline_output, baseline_msgs = run_claude(
        baseline_cmd, timeout_seconds=timeout_seconds, cwd=baseline_workdir,
        on_message=baseline_cb,
    )
    baseline = RunResult(
        case_id=case_id, variant="baseline",
        raw_output=baseline_output, model=model, timestamp=now,
        messages=baseline_msgs,
        command=" ".join(baseline_cmd),
    )

    skill_workdir = _make_workdir(case_id, "with_skill", fixture_dir=fixture_dir)
    skill_cmd = build_command(
        prompt, plugin_dirs=plugin_dirs, model=model, max_budget_usd=max_budget_usd,
    )
    skill_cb = (lambda msg: on_message("with_skill", msg)) if on_message else None
    skill_output, skill_msgs = run_claude(
        skill_cmd, timeout_seconds=timeout_seconds, cwd=skill_workdir,
        on_message=skill_cb,
    )
    with_skill = RunResult(
        case_id=case_id, variant="with_skill",
        raw_output=skill_output, model=model, timestamp=now,
        messages=skill_msgs,
        command=" ".join(skill_cmd),
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
