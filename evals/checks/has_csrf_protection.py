"""Fail if form handling lacks CSRF protection.

Looks for CSRF token usage, flask-wtf / CSRFProtect, or equivalent
middleware.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

CSRF_PATTERNS = [
    r"CSRFProtect\s*\(",
    r"csrf_protect|csrf\.init_app",
    r"flask_wtf|FlaskForm",
    r"csrf_token",
    r"WTF_CSRF|CSRF_ENABLED",
    r"@csrf\.",
    r"_csrf|csrfmiddleware|CsrfViewMiddleware",
    r"X-CSRF-Token|X-CSRFToken",
    r"anti.?forgery|AntiForgery",
]


def main() -> int:
    code = get_all_code(sys.stdin.read(), strip_docs=False)
    if not code.strip():
        return fail("No code found")

    if any(re.search(pat, code, re.IGNORECASE) for pat in CSRF_PATTERNS):
        return 0

    return fail(
        "Form handler has no CSRF protection — use flask-wtf CSRFProtect, "
        "include a csrf_token in forms, or add CSRF middleware"
    )


if __name__ == "__main__":
    sys.exit(main())
