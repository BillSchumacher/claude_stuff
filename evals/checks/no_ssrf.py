"""Fail if code fetches a user-supplied URL without any validation.

Safe alternatives: validate URL scheme (http/https), allowlist hosts,
block private/internal IP ranges, or use urlparse to inspect components.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

VALIDATION_PATTERNS = [
    r"urlparse\s*\(",
    r"scheme\s*(?:==|!=|not in|in\s)",
    r"allowlist|whitelist|allowed_hosts|allowed_domains",
    r"(?:127\.|10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.|169\.254\.|0\.0\.0\.0)",
    r"ipaddress\.ip_address|is_private|is_loopback|is_link_local",
    r"validators\.url\s*\(",
]


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    # Check if code fetches a URL from user input
    fetches_url = re.search(
        r"requests\.(?:get|post|put|head)\s*\(|"
        r"urllib\.request\.urlopen\s*\(|"
        r"httpx\.(?:get|post|AsyncClient)\s*\(",
        code,
    )
    if not fetches_url:
        return 0  # No URL fetching detected

    if any(re.search(pat, code) for pat in VALIDATION_PATTERNS):
        return 0

    return fail(
        "URL fetched from user input without validation — validate scheme, "
        "check against an allowlist, or block private IP ranges to prevent SSRF"
    )


if __name__ == "__main__":
    sys.exit(main())
