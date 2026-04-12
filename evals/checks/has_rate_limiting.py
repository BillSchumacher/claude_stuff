"""Check that security-sensitive endpoints include rate limiting.

Looks for rate limiting libraries, middleware, or decorators in the code.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, detect_target_language, fail

RATE_LIMIT_PATTERNS = [
    # Python
    r"ratelimit|rate_limit|RateLimit|slowapi|Limiter|throttle",
    # JavaScript / TypeScript
    r"express-rate-limit|rateLimit|rate-limit|throttle",
    # Go
    r"golang\.org/x/time/rate|rate\.NewLimiter|httprate",
    # PHP
    r"RateLimiter|throttle|ThrottleRequests",
    # C#
    r"RateLimiting|UseRateLimiter|RateLimitPartition",
    # General patterns
    r"rate.limit|rateLimiter|rate_limiter|too.many.requests|429|Retry-After",
    # Nginx / infrastructure
    r"limit_req|limit_conn",
]


def main() -> int:
    stdin = sys.stdin.read()
    lang = detect_target_language()

    if lang in ("go", "javascript", "typescript", "php", "csharp", "rust", "c", "cpp"):
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
            languages=("python", "py", "go", "golang", "javascript", "js",
                        "typescript", "ts", "php", "csharp", "cs", "rust", "rs"),
            strip_docs=False,
        )

    # Also check raw output text for rate limiting discussion
    text = stdin + "\n" + code

    if not text.strip():
        return fail("No output found")

    for pattern in RATE_LIMIT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return 0

    return fail(
        "No rate limiting found. Expected rate limiting middleware, "
        "decorator, or library for security-sensitive endpoints."
    )


if __name__ == "__main__":
    sys.exit(main())
