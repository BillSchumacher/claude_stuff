"""Run automated checks (linters, scripts) against Claude's output."""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

from src.config import RunResult, CheckRow


def extract_code_blocks(output: str) -> list[str]:
    """Extract fenced code blocks from markdown output."""
    return re.findall(r"```(?:\w*)\n(.*?)```", output, re.DOTALL)


def run_linter(
    code: str,
    linter: str,
    case_id: str,
    variant: str,
    *,
    timeout_seconds: int = 30,
) -> CheckRow:
    """Write code to a temp file, run a linter, return pass/fail."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8",
    ) as f:
        f.write(code)
        tmp_path = f.name
    try:
        linter_cmd = linter.split() + [tmp_path]
        result = subprocess.run(
            linter_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return CheckRow(
            case_id=case_id,
            variant=variant,
            check_name=linter,
            passed=result.returncode == 0,
            detail=result.stdout.strip() or result.stderr.strip(),
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def run_check_script(
    output: str,
    script_path: Path,
    case_id: str,
    variant: str,
    *,
    messages: list[dict] | None = None,
    expected_skills: list[str] | None = None,
    timeout_seconds: int = 30,
) -> CheckRow:
    """Run a custom check script with output on stdin and messages in a temp file.

    The EVAL_MESSAGES_FILE env var points to a temp JSON file containing
    the full stream-json messages, so scripts can analyze execution order.
    The EVAL_EXPECTED_SKILLS env var contains comma-separated expected skill names.
    """
    env = {**os.environ}
    msgs_path = None
    if messages:
        msgs_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
        )
        json.dump(messages, msgs_file)
        msgs_file.close()
        msgs_path = msgs_file.name
        env["EVAL_MESSAGES_FILE"] = msgs_path
    if expected_skills:
        env["EVAL_EXPECTED_SKILLS"] = ",".join(expected_skills)
    try:
        result = subprocess.run(
            ["python", str(script_path)],
            input=output,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
    finally:
        if msgs_path:
            Path(msgs_path).unlink(missing_ok=True)
    return CheckRow(
        case_id=case_id,
        variant=variant,
        check_name=script_path.name,
        passed=result.returncode == 0,
        detail=result.stderr.strip(),
    )


def check_output(
    result: RunResult,
    linters: list[str],
    scripts: list[Path],
    *,
    expected_skills: list[str] | None = None,
) -> Iterator[CheckRow]:
    """Run all checks against a single output, yielding CheckRows."""
    code_blocks = extract_code_blocks(result.raw_output)

    for linter in linters:
        if not code_blocks:
            yield CheckRow(
                case_id=result.case_id,
                variant=result.variant,
                check_name=linter,
                passed=False,
                detail="No code blocks found in output",
            )
            continue
        # Lint each block independently to avoid false positives
        # from duplicate definitions across separate files
        failures = []
        for block in code_blocks:
            row = run_linter(block, linter, result.case_id, result.variant)
            if not row["passed"]:
                failures.append(row["detail"])
        yield CheckRow(
            case_id=result.case_id,
            variant=result.variant,
            check_name=linter,
            passed=len(failures) == 0,
            detail="\n---\n".join(failures),
        )

    for script_path in scripts:
        yield run_check_script(
            result.raw_output, script_path, result.case_id, result.variant,
            messages=result.messages,
            expected_skills=expected_skills,
        )
