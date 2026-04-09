"""Score outputs against rubric criteria using a second Claude call as judge."""

import json
import re
from typing import Iterator

from src.config import RunResult, ScoreRow
from src.runner import run_claude_json

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
) -> list[ScoreRow]:
    """Score a single output against the rubric."""
    prompt = build_judge_prompt(task_prompt, output, criteria)
    cmd = [
        "claude", "-p",
        "--disable-slash-commands",
        "--output-format", "json",
        "--model", model,
        "--append-system-prompt", JUDGE_SYSTEM_PROMPT,
        prompt,
    ]
    raw = run_claude_json(cmd)
    scores = parse_judge_response(raw)
    return [
        ScoreRow(
            case_id=case_id,
            variant=variant,
            criterion=s["criterion"],
            score=s["score"],
            explanation=s["explanation"],
        )
        for s in scores
    ]


def score_pair(
    task_prompt: str,
    with_skill: RunResult,
    baseline: RunResult,
    criteria: list[str],
    *,
    model: str = "sonnet",
) -> Iterator[ScoreRow]:
    """Score both variants of a case, yielding ScoreRows."""
    yield from score_output(
        task_prompt, baseline.raw_output, criteria,
        baseline.case_id, baseline.variant, model=model,
    )
    yield from score_output(
        task_prompt, with_skill.raw_output, criteria,
        with_skill.case_id, with_skill.variant, model=model,
    )
