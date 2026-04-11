"""Fail if code returns a resource without checking ownership (IDOR).

Looks for a comparison between the resource's owner/user_id and the
current authenticated user before returning data.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

AUTHZ_PATTERNS = [
    r"user_id\s*[!=]=",
    r"owner\s*[!=]=",
    r"belongs_to|owned_by",
    r"current_user\.\w+\s*[!=]=",
    r"get_current_user\(\).*[!=]=",
    r"abort\s*\(\s*403",
    r"Forbidden|Unauthorized|not\s+authorized",
    r"if\s+order\[.*user",
    r"if\s+\w+\.user",
]


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    if any(re.search(pat, code, re.IGNORECASE) for pat in AUTHZ_PATTERNS):
        return 0

    return fail(
        "Resource returned without ownership check — verify the resource "
        "belongs to the current user before returning it (IDOR prevention)"
    )


if __name__ == "__main__":
    sys.exit(main())
