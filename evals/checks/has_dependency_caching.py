"""Fail if CI/CD pipeline does not cache dependencies.

Looks for: setup action `cache:` parameter, `actions/cache@`, or
`hashFiles(` in cache key. Language-aware.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

CACHE_PATTERNS = [
    r"cache\s*:\s*['\"]?\w+",            # setup action cache: 'pip', 'npm', etc.
    r"cache\s*:\s*true",                  # setup action cache: true
    r"actions/cache@",                    # explicit cache action
    r"Swatinem/rust-cache@",             # Rust-specific cache action
    r"hendrikmuhs/ccache-action@",       # C/C++ ccache action
    r"hashFiles\s*\(",                   # cache key with lockfile hash
    r"restore-keys\s*:",                 # cache restore fallback
]


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("yaml", "yml"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No YAML workflow found")

    if any(re.search(pat, code, re.IGNORECASE) for pat in CACHE_PATTERNS):
        return 0

    return fail(
        "CI/CD pipeline does not cache dependencies — "
        "use the setup action's cache parameter or actions/cache"
    )


if __name__ == "__main__":
    sys.exit(main())
