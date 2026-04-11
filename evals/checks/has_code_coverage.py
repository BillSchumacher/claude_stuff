"""Fail if CI/CD pipeline does not generate code coverage.

Looks for coverage flags, tools, or upload steps across all languages.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

COVERAGE_PATTERNS = [
    # Python
    r"--cov\b",
    r"pytest-cov|coverage\.xml",
    # JavaScript / TypeScript
    r"--coverage\b",
    r"coverageReporters|coverageThreshold",
    r"vitest.*coverage|coverage\.reporter",
    # Go
    r"-coverprofile",
    r"coverage\.out",
    r"gocover-cobertura",
    # Rust
    r"tarpaulin|llvm-cov|cargo-llvm-cov",
    # PHP
    r"--coverage-clover|coverage-clover",
    r"phpunit.*coverage|pcov|xdebug",
    # C#
    r"XPlat Code Coverage|CollectCoverage|coverlet",
    # C/C++
    r"gcov|lcov|gcovr",
    r"--coverage",
    # Universal
    r"codecov|coveralls|upload.*coverage|coverage.*upload",
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

    if any(re.search(pat, code, re.IGNORECASE) for pat in COVERAGE_PATTERNS):
        return 0

    return fail(
        "CI/CD pipeline does not generate code coverage — "
        "add a coverage step and upload results"
    )


if __name__ == "__main__":
    sys.exit(main())
