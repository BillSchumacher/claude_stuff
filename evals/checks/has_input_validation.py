"""Fail if code accepts user input without any validation.

Looks for at least two distinct validation patterns: type checks, length
limits, format validation, abort/raise on bad input, or use of a validation
library.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

VALIDATION_PATTERNS = [
    r"isinstance\s*\(",
    r"raise\s+(?:ValueError|TypeError|BadRequest|ValidationError)",
    r"abort\s*\(\s*4[02]\d",
    r"\.validate\s*\(",
    r"(?:marshmallow|pydantic|cerberus|voluptuous|jsonschema)",
    r"re\.(?:match|search|fullmatch)\s*\(",
    r"len\s*\([^)]*\)\s*[<>!=]",
    r"not\s+.*\bor\b.*\braise\b",
    r"if\s+not\s+\w+",
    r"@validates",
]


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    hits = sum(1 for pat in VALIDATION_PATTERNS if re.search(pat, code))
    if hits < 2:
        return fail(
            f"Only {hits} validation pattern(s) found — "
            "expected at least 2 (type check, length, format, abort, etc.)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
