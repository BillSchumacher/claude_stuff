"""Fail if session cookies are set without security flags.

Checks for HttpOnly, Secure, and SameSite flags on set_cookie calls
or session configuration.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    code_lower = code.lower()

    flags = {
        "httponly": bool(re.search(r"httponly\s*=\s*True", code, re.IGNORECASE)),
        "secure": bool(re.search(r"(?<!\w)secure\s*=\s*True", code, re.IGNORECASE)),
        "samesite": bool(re.search(r"samesite\s*=", code, re.IGNORECASE)),
    }

    # Also check session config (Flask SESSION_COOKIE_* settings)
    if "session_cookie_httponly" in code_lower:
        flags["httponly"] = True
    if "session_cookie_secure" in code_lower:
        flags["secure"] = True
    if "session_cookie_samesite" in code_lower:
        flags["samesite"] = True

    present = [k for k, v in flags.items() if v]
    missing = [k for k, v in flags.items() if not v]

    if len(present) < 2:
        return fail(
            f"Cookie missing security flags: {', '.join(missing)} — "
            "set HttpOnly, Secure, and SameSite on session cookies"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
