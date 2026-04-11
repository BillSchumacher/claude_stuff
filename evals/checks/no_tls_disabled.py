"""Fail if TLS verification is disabled.

Multi-language: Python verify=False, Go InsecureSkipVerify, JS rejectUnauthorized,
Rust danger_accept_invalid_certs.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

BAD_PATTERNS = [
    # Python
    (r"verify\s*=\s*False", "verify=False"),
    (r"VERIFY_NONE", "VERIFY_NONE"),
    (r"CERT_NONE", "CERT_NONE"),
    (r"check_hostname\s*=\s*False", "check_hostname=False"),
    (r"ssl\._create_unverified_context", "_create_unverified_context"),
    (r"InsecureRequestWarning", "disabling InsecureRequestWarning"),
    # Go
    (r"InsecureSkipVerify\s*:\s*true", "InsecureSkipVerify"),
    # JavaScript / Node.js
    (r"rejectUnauthorized\s*:\s*false", "rejectUnauthorized: false"),
    (r"NODE_TLS_REJECT_UNAUTHORIZED.*['\"]0['\"]", "NODE_TLS_REJECT_UNAUTHORIZED=0"),
    (r"process\.env\.NODE_TLS_REJECT_UNAUTHORIZED", "disabling NODE_TLS verification"),
    # Rust
    (r"danger_accept_invalid_certs\s*\(\s*true\s*\)", "danger_accept_invalid_certs(true)"),
    # C#
    (r"ServerCertificateValidationCallback\s*=.*true", "bypassing certificate validation"),
]


def main() -> int:
    stdin = sys.stdin.read()
    code = get_all_code(
        stdin,
        languages=(
            "python", "py", "go", "golang", "javascript", "js",
            "typescript", "ts", "php", "csharp", "cs", "rust", "rs",
            "c", "cpp", "c++",
        ),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No code found")

    for pattern, label in BAD_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return fail(f"TLS verification disabled: {label}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
