"""Score outputs against rubric criteria using a second Claude call as judge."""

import json
import re
from typing import Callable

from src.config import RunResult, ScoreRow, ROOT
from src.runner import run_claude, _ISOLATION_SETTINGS

JUDGE_SYSTEM_PROMPT = (
    "You are an evaluation judge. You will be given a task prompt, "
    "an output to evaluate, and a list of criteria.\n\n"
    "For each criterion, score 0 (not met), 1 (partially met), or 2 (fully met).\n\n"
    "You MUST respond with ONLY a JSON object in this exact format, no other text:\n"
    '{"scores": [{"criterion": "...", "score": 0, "explanation": "..."}]}'
)


def build_judge_prompt(
    task_prompt: str,
    output: str,
    criteria: list[str],
) -> str:
    """Compose the prompt sent to the judge model."""
    criteria_text = "\n".join(f"- {c}" for c in criteria)
    return (
        f"## Task Prompt\n{task_prompt}\n\n"
        f"## Output to Evaluate\n{output}\n\n"
        f"## Criteria\n{criteria_text}\n\n"
        "Score each criterion 0-2. Respond with ONLY the JSON object."
    )


def parse_judge_response(raw: str) -> list[dict]:
    """Extract scores array from judge response, handling markdown fences."""
    # Try direct JSON parse first
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed.get("scores", [parsed])
        return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Try extracting JSON from markdown code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, dict):
                return parsed.get("scores", [parsed])
            return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # Try finding JSON object/array in the text
    for pattern in [r"\{.*\}", r"\[.*\]"]:
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed.get("scores", [parsed])
                return parsed
            except (json.JSONDecodeError, ValueError):
                continue

    raise ValueError(f"Could not parse judge response as JSON: {raw[:200]}")


def score_output(
    task_prompt: str,
    output: str,
    criteria: list[str],
    case_id: str,
    variant: str,
    *,
    model: str = "sonnet",
    on_judge_message: Callable[[str, dict], None] | None = None,
) -> tuple[list[ScoreRow], str, list[dict], str]:
    """Score a single output against the rubric.

    on_judge_message: optional callback for live streaming of judge messages.
    Returns (score_rows, raw_judge_response, judge_messages, command).
    """
    prompt = build_judge_prompt(task_prompt, output, criteria)
    judge_plugin = ROOT / "plugins" / "code-judge"
    cmd = [
        "claude",
        "--verbose",
        "--output-format", "stream-json",
        "--model", model,
        "--plugin-dir", str(judge_plugin.resolve()),
        "--append-system-prompt", JUDGE_SYSTEM_PROMPT,
        "--settings", _ISOLATION_SETTINGS,
        "-p", prompt,
    ]

    phase = f"score:{variant}"
    cb = (lambda msg: on_judge_message(phase, msg)) if on_judge_message else None
    raw, messages = run_claude(cmd, on_message=cb)
    scores = parse_judge_response(raw)
    score_rows = [
        ScoreRow(
            case_id=case_id,
            variant=variant,
            criterion=s["criterion"],
            score=s["score"],
            explanation=s["explanation"],
        )
        for s in scores
    ]
    return score_rows, raw, messages, " ".join(cmd)


def enrich_with_written_files(result: RunResult) -> str:
    """Combine the agent's text response with any files it wrote via the Write tool.

    Without this, the judge only sees the summary text and gives partial scores
    for code it can't directly verify.
    """
    parts = [result.raw_output]
    for msg in result.messages:
        if msg.get("type") != "assistant":
            continue
        for content in msg.get("message", {}).get("content", []):
            if content.get("type") == "tool_use" and content.get("name") == "Write":
                inp = content.get("input", {})
                path = inp.get("file_path", "")
                file_content = inp.get("content", "")
                if file_content:
                    parts.append(f"\n\n## File: {path}\n```\n{file_content}\n```")
    return "\n".join(parts)


def score_pair(
    task_prompt: str,
    with_skill: RunResult,
    baseline: RunResult,
    criteria: list[str],
    *,
    model: str = "sonnet",
    on_judge_message: Callable[[str, dict], None] | None = None,
) -> dict:
    """Score both variants of a case.

    Returns dict with 'rows' (list[ScoreRow]) and 'judge_runs' (list of judge
    execution records for saving to the DB).
    """
    rows = []
    judge_runs = []

    bl_rows, bl_raw, bl_msgs, bl_cmd = score_output(
        task_prompt, enrich_with_written_files(baseline), criteria,
        baseline.case_id, baseline.variant, model=model,
        on_judge_message=on_judge_message,
    )
    rows.extend(bl_rows)
    judge_runs.append({
        "variant": "judge:score:baseline",
        "raw_output": bl_raw,
        "messages": bl_msgs,
        "command": bl_cmd,
    })

    sk_rows, sk_raw, sk_msgs, sk_cmd = score_output(
        task_prompt, enrich_with_written_files(with_skill), criteria,
        with_skill.case_id, with_skill.variant, model=model,
        on_judge_message=on_judge_message,
    )
    rows.extend(sk_rows)
    judge_runs.append({
        "variant": "judge:score:with_skill",
        "raw_output": sk_raw,
        "messages": sk_msgs,
        "command": sk_cmd,
    })

    return {"rows": rows, "judge_runs": judge_runs}
