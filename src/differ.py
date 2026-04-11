"""Compare with-skill vs baseline outputs."""

import difflib

from src.config import RunResult
from src.runner import run_claude_json


def compute_diff(baseline: str, with_skill: str) -> str:
    """Compute a unified diff between baseline and with-skill outputs."""
    baseline_lines = baseline.splitlines(keepends=True)
    skill_lines = with_skill.splitlines(keepends=True)
    diff = difflib.unified_diff(
        baseline_lines, skill_lines,
        fromfile="baseline", tofile="with_skill",
    )
    return "".join(diff)


def summarize_diff(
    task_prompt: str,
    baseline: str,
    with_skill: str,
    *,
    model: str = "opus",
) -> str:
    """Use a Claude call to summarize the meaningful differences."""
    prompt = (
        "Compare these two outputs for the same task and summarize "
        "the meaningful differences in 2-3 sentences.\n\n"
        f"## Task\n{task_prompt}\n\n"
        f"## Baseline Output\n{baseline}\n\n"
        f"## With-Skill Output\n{with_skill}"
    )
    cmd = [
        "claude", "-p",
        "--disable-slash-commands",
        "--output-format", "json",
        "--model", model,
    ]
    return run_claude_json(cmd, stdin_text=prompt)


def diff_pair(
    baseline: RunResult,
    with_skill: RunResult,
    task_prompt: str,
    *,
    model: str = "opus",
) -> dict[str, str]:
    """Produce both raw diff and AI summary for a result pair."""
    raw = compute_diff(baseline.raw_output, with_skill.raw_output)
    summary = summarize_diff(
        task_prompt, baseline.raw_output, with_skill.raw_output,
        model=model,
    )
    return {"raw_diff": raw, "summary": summary}
