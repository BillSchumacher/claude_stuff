"""Fail if C++ CI combines AddressSanitizer with coverage in the same build.

ASan and gcov/lcov coverage flags conflict — ASan intercepts memory
operations that confuse the coverage counter. Use separate build
configurations for coverage and sanitizers.
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

    has_asan = re.search(r"-fsanitize=address|fsanitize.*address", code)
    has_coverage = re.search(r"--coverage|gcov|lcov|gcovr", code)

    if not has_asan or not has_coverage:
        return 0  # Doesn't have both, N/A

    # Check if they're in the same step/job or separate jobs
    # Simple heuristic: if there's a job boundary between them, it's OK
    asan_pos = has_asan.start()
    cov_pos = has_coverage.start()

    # Look for job boundaries (lines starting with whitespace + name + colon)
    between = code[min(asan_pos, cov_pos):max(asan_pos, cov_pos)]
    if re.search(r"^\s{2}\w[\w-]+:\s*$", between, re.MULTILINE):
        return 0  # Different jobs

    return fail(
        "ASan and coverage flags in the same build configuration — "
        "use separate jobs; ASan interferes with coverage counters"
    )


if __name__ == "__main__":
    sys.exit(main())
