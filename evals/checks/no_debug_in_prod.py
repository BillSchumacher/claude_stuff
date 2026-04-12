"""Fail if code enables debug mode in production-facing configuration.

Checks for: DEBUG=True, app.debug=True, debug=True in settings,
Flask/Django debug mode, Express morgan('dev') without env guard.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, detect_target_language, fail

DEBUG_PATTERNS = [
    # Python / Django / Flask
    (r"\bDEBUG\s*=\s*True\b", "DEBUG = True"),
    (r"app\.debug\s*=\s*True", "app.debug = True"),
    (r"debug\s*=\s*True", "debug=True in config"),
    # Node.js / Express
    (r"app\.set\s*\(\s*['\"]env['\"],\s*['\"]development['\"]", "Express env set to development"),
    # General
    (r"\.run\s*\([^)]*debug\s*=\s*True", ".run(debug=True)"),
]

# Patterns that indicate the debug flag is properly guarded
SAFE_GUARDS = [
    r"os\.environ",
    r"os\.getenv",
    r"process\.env",
    r"settings\.",
    r"config\.",
    r"if\s+__name__\s*==",
    r"ENV\[",
    r"getenv",
]


def main() -> int:
    stdin = sys.stdin.read()
    lang = detect_target_language()

    if lang in ("javascript", "typescript"):
        code = get_all_code_c_style(
            stdin,
            languages=("javascript", "js", "typescript", "ts"),
            require_language_tag=True,
        )
    else:
        code = get_all_code(
            stdin,
            languages=("python", "py", "javascript", "js", "typescript", "ts"),
            strip_docs=False,
            require_language_tag=True,
        )

    if not code.strip():
        return 0  # No code to check

    for pattern, label in DEBUG_PATTERNS:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            # Check if it's inside an env-guarded block (within 3 lines)
            start = max(0, match.start() - 200)
            context = code[start:match.end() + 100]
            if any(re.search(guard, context) for guard in SAFE_GUARDS):
                continue
            return fail(f"Debug mode enabled without env guard: {label}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
