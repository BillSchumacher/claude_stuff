"""Fail if error handling swallows exceptions (fail-open).

Detects: bare `except: pass`, `except Exception: pass`, or exception
handlers that silently continue instead of returning an error or re-raising.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

# except (with optional type) followed by pass/continue within 2 lines
SWALLOW_PATTERNS = [
    r"except\s*:\s*\n\s*pass",
    r"except\s+\w+\s*:\s*\n\s*pass",
    r"except\s+\w+\s*:\s*\n\s*continue",
    r"except\s*:\s*\n\s*continue",
    r"except\s+Exception\s*(as\s+\w+\s*)?:\s*\n\s*pass",
]


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    for pat in SWALLOW_PATTERNS:
        if re.search(pat, code):
            return fail(
                "Exception silently swallowed (fail-open) — handle errors "
                "explicitly: return an error response, re-raise, or log and abort"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
