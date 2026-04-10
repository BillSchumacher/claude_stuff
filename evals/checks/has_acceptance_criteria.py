"""Check that the output includes explicit requirements + Given/When/Then acceptance criteria."""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_written_content, fail


def get_full_text(stdin: str) -> str:
    """Combine stdin output with all written file contents."""
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

    lower = text.lower()

    # 1. Must mention requirements or acceptance criteria as a section heading.
    # Accept any markdown heading level (#, ##, ###, ####) optionally with a
    # leading number ("### 1. Requirements") and bold prose markers.
    has_section = bool(
        re.search(
            r"^#{1,6}\s*(?:\d+\.\s*)?(requirements|acceptance criteria|"
            r"functional requirements|acceptance tests)\b",
            lower,
            re.MULTILINE,
        )
        or re.search(
            r"\*\*\s*(?:\d+\.\s*)?(requirements|acceptance criteria)",
            lower,
        )
    )
    if not has_section:
        return fail("No 'Requirements' or 'Acceptance Criteria' section heading found")

    # 2. Must contain at least one Given / When / Then
    has_gwt = ("given" in lower) and ("when" in lower) and ("then" in lower)
    if not has_gwt:
        return fail("No Given/When/Then acceptance criteria found")

    # 3. Must contain at least one numbered requirement using "shall"
    shall_count = len(re.findall(r"\bshall\b", lower))
    if shall_count < 2:
        return fail(
            f"Fewer than 2 'shall' requirement statements found ({shall_count})"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
