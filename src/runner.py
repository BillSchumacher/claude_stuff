"""Run claude -p with and without plugins, capture output."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
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

# Module-level handle for the Windows Job Object (kept alive for process lifetime).
_job_handle = None


def setup_child_cleanup() -> None:
    """Ensure all subprocess descendants are killed when this process exits.

    On Windows, uses a Job Object with KILL_ON_JOB_CLOSE so that every
    descendant process (claude, flask, dev servers, etc.) is terminated
    when the current Python process exits for any reason.
    On Unix, relies on start_new_session in Popen calls.
    """
    global _job_handle
    if _job_handle is not None:
        return
    if sys.platform != "win32":
        return

    import ctypes
    from ctypes import wintypes

    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL

        class _BasicLimitInfo(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32),
            ]

        class _IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class _ExtendedLimitInfo(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BasicLimitInfo),
                ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x0800
        JobObjectExtendedLimitInformation = 9

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return

        info = _ExtendedLimitInfo()
        info.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK
        )

        if not kernel32.SetInformationJobObject(
            job, JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info),
        ):
            kernel32.CloseHandle(job)
            return

        current = kernel32.GetCurrentProcess()
        if not kernel32.AssignProcessToJobObject(job, current):
            kernel32.CloseHandle(job)
            return

        # Keep handle alive for the lifetime of the process — never close it.
        _job_handle = job
    except Exception:
        pass


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
    stdin_text: str | None = None,
) -> tuple[str, list[dict]]:
    """Execute a claude command with stream-json output. Returns (response_text, messages).

    on_message: if provided, called with each parsed JSON message as it arrives
    (enables live streaming to the UI). Falls back to batch mode if not set.

    stdin_text: if provided, pipe as stdin. Required for large prompts that
    exceed the Windows CreateProcess 32KB command-line limit — pass `-p` in
    cmd without a value and provide the prompt here instead.

    Retries once on non-zero exit (transient init failures, API errors).
    """
    if on_message:
        return _run_claude_streaming(
            cmd, timeout_seconds=timeout_seconds, cwd=cwd,
            on_message=on_message,
            stdin_text=stdin_text,
        )

    for attempt in range(2):
        result = _exec(
            cmd, timeout_seconds=timeout_seconds, cwd=cwd,
            stdin_text=stdin_text,
        )
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
    stdin_text: str | None = None,
) -> tuple[str, list[dict]]:
    """Run claude and stream each JSON message as it arrives.

    stdin_text: if provided, fed to the child's stdin in a background thread
    so large prompts don't deadlock on a full pipe buffer before we drain stdout.
    """
    env = {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
    )

    if stdin_text is not None:
        def _feed_stdin() -> None:
            try:
                assert proc.stdin is not None
                proc.stdin.write(stdin_text.encode("utf-8"))
            except (BrokenPipeError, OSError):
                pass
            finally:
                try:
                    if proc.stdin is not None:
                        proc.stdin.close()
                except OSError:
                    pass
        threading.Thread(target=_feed_stdin, daemon=True).start()

    messages = []
    result_text = ""
    deadline = time.time() + timeout_seconds

    assert proc.stdout is not None
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


def _snapshot_plugins(plugin_dirs: list[Path], case_id: str, model: str) -> list[Path]:
    """Copy plugins to an ephemeral dir so agent writes don't pollute the repo.

    Claude CLI surfaces the --plugin-dir path to the agent via its system prompt,
    and some agents (notably haiku on rust-oriented skills) decide to write their
    implementation into that path rather than the cwd. Snapshotting keeps the
    real plugin sources in the repo untouched.
    """
    if not plugin_dirs:
        return []
    timestamp = int(time.time() * 1000)
    snapshot_root = (
        Path(tempfile.gettempdir()) / "skill_eval"
        / f"plugins_{case_id}_{model}_{timestamp}"
    )
    snapshot_root.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for src in plugin_dirs:
        dst = snapshot_root / src.name
        shutil.copytree(src, dst)
        snapshots.append(dst)
    return snapshots


def _make_workdir(
    case_id: str,
    variant: str,
    *,
    model: str = "",
    fixture_dir: Path | None = None,
) -> str:
    """Create a fresh isolated working directory for a variant run.

    Directory name includes model and timestamp so concurrent runs with
    different models do not collide.  If fixture_dir is provided, copies
    its contents into the workdir and initialises a git repo.
    """
    timestamp = int(time.time() * 1000)
    name = f"{case_id}_{variant}_{model}_{timestamp}" if model else f"{case_id}_{variant}_{timestamp}"
    workdir = Path(tempfile.gettempdir()) / "skill_eval" / name
    if workdir.exists():
        try:
            shutil.rmtree(workdir)
        except PermissionError:
            workdir = workdir.with_name(f"{name}_{int(time.time())}")
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
    plugin_dirs = _snapshot_plugins(
        [resolve_plugin_path(name) for name in plugins],
        case_id, model,
    )

    baseline_workdir = _make_workdir(
        case_id, "baseline", model=model, fixture_dir=fixture_dir,
    )
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

    skill_workdir = _make_workdir(
        case_id, "with_skill", model=model, fixture_dir=fixture_dir,
    )
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
