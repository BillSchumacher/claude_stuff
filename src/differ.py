"""Compare with-skill vs baseline outputs by reconstructing file states."""

import difflib
import re
from typing import Callable

from src.config import RunResult, ROOT
from src.runner import run_claude, _ISOLATION_SETTINGS


def extract_file_states(messages: list[dict]) -> dict[str, str]:
    """Reconstruct the final state of all files from Write/Edit tool calls.

    Processes messages in order, applying Write (full replace) and Edit
    (find-and-replace) operations to build up the final file contents.
    """
    files: dict[str, str] = {}

    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        for content in msg.get("message", {}).get("content", []):
            if content.get("type") != "tool_use":
                continue

            name = content.get("name", "")
            inp = content.get("input", {})

            if name == "Write":
                path = inp.get("file_path", "")
                file_content = inp.get("content", "")
                if path and file_content:
                    # Normalize path to just the filename/relative part
                    path = _normalize_path(path)
                    files[path] = file_content

            elif name == "Edit":
                path = inp.get("file_path", "")
                old_string = inp.get("old_string", "")
                new_string = inp.get("new_string", "")
                if path and old_string:
                    path = _normalize_path(path)
                    if path in files:
                        files[path] = files[path].replace(old_string, new_string, 1)
                    else:
                        # Edit on a file we haven't seen — store the edit as context
                        files[path] = f"(edited)\n--- old:\n{old_string}\n+++ new:\n{new_string}"

    return files


def _normalize_path(path: str) -> str:
    """Strip temp dir prefixes to get a comparable relative path."""
    # Remove common temp dir patterns
    path = path.replace("\\", "/")
    # Strip /tmp/skill_eval/case_id_variant/ or C:/Users/.../Temp/skill_eval/...
    match = re.search(r"skill_eval/[^/]+/(.*)", path)
    if match:
        return match.group(1)
    # Strip absolute paths to just the last components
    parts = path.split("/")
    # Keep last 2-3 path components for readability
    if len(parts) > 3:
        return "/".join(parts[-3:])
    return path


def compute_file_diffs(
    baseline_files: dict[str, str],
    skill_files: dict[str, str],
) -> str:
    """Compute unified diffs between baseline and skill file states."""
    all_paths = sorted(set(baseline_files) | set(skill_files))
    diffs = []

    for path in all_paths:
        bl_content = baseline_files.get(path, "")
        sk_content = skill_files.get(path, "")

        if bl_content == sk_content:
            continue

        bl_lines = bl_content.splitlines(keepends=True)
        sk_lines = sk_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            bl_lines, sk_lines,
            fromfile=f"baseline/{path}",
            tofile=f"with_skill/{path}",
        )
        diff_text = "".join(diff)
        if diff_text:
            diffs.append(diff_text)

    if not diffs:
        return "(no file differences)"

    return "\n".join(diffs)


def summarize_diff(
    task_prompt: str,
    baseline_files: dict[str, str],
    skill_files: dict[str, str],
    *,
    model: str = "sonnet",
    on_judge_message: Callable[[str, dict], None] | None = None,
) -> tuple[str, list[dict], str]:
    """Use a Claude call to summarize the meaningful differences.

    Returns (summary_text, judge_messages, command).
    """
    bl_summary = _files_summary(baseline_files, "Baseline")
    sk_summary = _files_summary(skill_files, "With-Skill")

    prompt = (
        "Compare the files produced by two variants of the same task. "
        "Summarize the meaningful differences in 2-3 sentences.\n\n"
        f"## Task\n{task_prompt}\n\n"
        f"{bl_summary}\n\n"
        f"{sk_summary}"
    )
    judge_plugin = ROOT / "plugins" / "code-judge"
    cmd = [
        "claude",
        "--verbose",
        "--output-format", "stream-json",
        "--model", model,
        "--plugin-dir", str(judge_plugin.resolve()),
        "--settings", _ISOLATION_SETTINGS,
        "-p", prompt,
    ]
    cb = (lambda msg: on_judge_message("diff", msg)) if on_judge_message else None
    raw, messages = run_claude(cmd, on_message=cb)
    return raw, messages, " ".join(cmd)


def _files_summary(files: dict[str, str], label: str) -> str:
    """Build a truncated summary of file contents for the judge."""
    if not files:
        return f"## {label}\n(no files written)"
    parts = [f"## {label} ({len(files)} files)"]
    for path, content in sorted(files.items()):
        truncated = content[:3000]
        if len(content) > 3000:
            truncated += f"\n... ({len(content) - 3000} more chars)"
        parts.append(f"### {path}\n```\n{truncated}\n```")
    return "\n\n".join(parts)


def diff_pair(
    baseline: RunResult,
    with_skill: RunResult,
    task_prompt: str,
    *,
    model: str = "sonnet",
    on_judge_message: Callable[[str, dict], None] | None = None,
) -> dict:
    """Produce file-level diff and AI summary for a result pair."""
    bl_files = extract_file_states(baseline.messages)
    sk_files = extract_file_states(with_skill.messages)

    raw = compute_file_diffs(bl_files, sk_files)
    summary, judge_msgs, judge_cmd = summarize_diff(
        task_prompt, bl_files, sk_files, model=model,
        on_judge_message=on_judge_message,
    )
    return {
        "raw_diff": raw,
        "summary": summary,
        "judge_messages": judge_msgs,
        "judge_command": judge_cmd,
    }
