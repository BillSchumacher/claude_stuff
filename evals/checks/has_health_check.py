"""Check that a production service includes health check endpoints.

Looks for /healthz, /readyz, /health, /ready, /livez, or health check
route definitions.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, detect_target_language, fail

HEALTH_PATTERNS = [
    r"/health[z]?\b",
    r"/read[yz]\b",
    r"/live[z]?\b",
    r"/status\b",
    r"health.?check",
    r"HealthCheck",
    r"health_check",
    r"liveness",
    r"readiness",
    r"healthz",
]


def main() -> int:
    stdin = sys.stdin.read()
    lang = detect_target_language()

    if lang in ("go", "javascript", "typescript", "csharp", "rust", "php", "cpp"):
        code = get_all_code_c_style(
            stdin,
            languages=(
                "go", "golang", "javascript", "js", "typescript", "ts",
                "php", "csharp", "cs", "rust", "rs", "c", "cpp",
            ),
        )
    else:
        code = get_all_code(
            stdin,
            languages=("python", "py"),
            strip_docs=False,
        )

    text = stdin + "\n" + code

    if not text.strip():
        return fail("No output found")

    for pattern in HEALTH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return 0

    return fail(
        "No health check endpoint found. "
        "Expected /healthz (liveness) and /readyz (readiness) endpoints "
        "for production services."
    )


if __name__ == "__main__":
    sys.exit(main())
