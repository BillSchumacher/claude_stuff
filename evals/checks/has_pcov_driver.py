"""Fail if PHP CI uses xdebug as the coverage driver when pcov is faster.

pcov is 2-5x faster than xdebug for line coverage and produces identical
results. Use pcov in CI, reserve xdebug for local debugging.
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

    # If coverage is being generated, check the driver
    has_coverage = re.search(r"coverage|--coverage-clover", code, re.IGNORECASE)
    if not has_coverage:
        return 0  # No coverage step, N/A

    if re.search(r"\bpcov\b", code, re.IGNORECASE):
        return 0

    if re.search(r"\bxdebug\b", code, re.IGNORECASE):
        return fail(
            "PHP CI uses xdebug for coverage — use pcov instead; "
            "it's 2-5x faster and produces identical line coverage"
        )

    return 0  # Neither specified, could be fine


if __name__ == "__main__":
    sys.exit(main())
