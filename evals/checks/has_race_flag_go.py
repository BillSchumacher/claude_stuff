"""Fail if Go CI runs `go test` without the -race flag.

The race detector catches data races invisible without it. Always use
-race in CI.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("yaml", "yml"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No YAML workflow found")

    # Check if go test is present
    if not re.search(r"go test\b", code):
        return 0  # No go test found, N/A

    if re.search(r"-race", code):
        return 0

    return fail(
        "go test without -race flag — always use -race in CI to "
        "detect data races"
    )


if __name__ == "__main__":
    sys.exit(main())
