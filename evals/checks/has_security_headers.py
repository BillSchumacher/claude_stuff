"""Fail if the app does not set at least two security headers.

Checks for: Content-Security-Policy, X-Content-Type-Options,
X-Frame-Options, Strict-Transport-Security, Referrer-Policy,
Permissions-Policy.  Also counts flask-talisman or helmet usage.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

HEADERS = [
    r"Content-Security-Policy",
    r"X-Content-Type-Options",
    r"X-Frame-Options",
    r"Strict-Transport-Security",
    r"Referrer-Policy",
    r"Permissions-Policy",
]

# Libraries that set multiple headers at once
HEADER_LIBRARIES = [
    r"flask.?talisman|Talisman\s*\(",
    r"secure\.Secure\s*\(|import\s+secure",
]


def main() -> int:
    code = get_all_code(sys.stdin.read(), strip_docs=False)
    if not code.strip():
        return fail("No code found")

    # Libraries that bundle security headers count as full coverage
    if any(re.search(pat, code, re.IGNORECASE) for pat in HEADER_LIBRARIES):
        return 0

    found = [h for h in HEADERS if re.search(h, code, re.IGNORECASE)]
    if len(found) < 2:
        return fail(
            f"Only {len(found)} security header(s) set — "
            "set at least 2 of: CSP, X-Content-Type-Options, "
            "X-Frame-Options, HSTS, Referrer-Policy"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
