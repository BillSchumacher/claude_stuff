"""Fail if TLS verification is disabled (verify=False, InsecureSkipVerify, CERT_NONE)."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    bad_patterns = [
        (r"verify\s*=\s*False", "verify=False"),
        (r"VERIFY_NONE", "VERIFY_NONE"),
        (r"CERT_NONE", "CERT_NONE"),
        (r"check_hostname\s*=\s*False", "check_hostname=False"),
        (r"InsecureSkipVerify\s*:\s*true", "InsecureSkipVerify"),
        (r"InsecureRequestWarning", "explicitly disabling InsecureRequestWarning"),
        (r"ssl\._create_unverified_context", "_create_unverified_context"),
    ]
    for pattern, label in bad_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return fail(f"TLS verification disabled: {label}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
