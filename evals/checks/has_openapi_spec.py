"""Check that the output includes an OpenAPI 3.x spec fragment for the new endpoint(s)."""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_written_content, fail


def get_full_text(stdin: str) -> str:
    """Combine stdin with all Write tool contents (file content, regardless of language)."""
    text = stdin
    msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
    if msgs_file:
        with open(msgs_file, encoding="utf-8") as f:
            messages = json.load(f)
        text += "\n" + get_written_content(messages)
    return text


def main() -> int:
    text = get_full_text(sys.stdin.read())
    if not text.strip():
        return fail("No output")

    # Signal 1: OpenAPI 3.x identifier in YAML or JSON form
    has_openapi_marker = bool(
        re.search(r'\bopenapi:\s*["\']?3\.\d', text)
        or re.search(r'"openapi"\s*:\s*"3\.\d', text)
    )

    # Signal 2: structurally complete OpenAPI fragment
    has_paths_section = re.search(r"^\s*paths:\s*$", text, re.MULTILINE)
    has_responses_section = re.search(r"^\s*responses:\s*$", text, re.MULTILINE)
    has_structural_fragment = bool(has_paths_section and has_responses_section)

    # Signal 3: RFC 9457 problem+json error format (strong skill marker — vanilla
    # code uses {"error": "msg"} instead)
    has_problem_json = bool(
        re.search(r"application/problem\+json", text, re.IGNORECASE)
    )

    if not (has_openapi_marker or has_structural_fragment or has_problem_json):
        return fail(
            "No API design artifacts found. Expected one of: "
            "OpenAPI 3.x spec, paths/responses YAML block, "
            "or application/problem+json error format (RFC 9457)."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
