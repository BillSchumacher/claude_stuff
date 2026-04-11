"""Fail if CI/CD pipeline does not include a linting or static analysis step.

Looks for language-appropriate linters, formatters, and type checkers.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

LINT_PATTERNS = [
    # Python
    r"\bruff\b",
    r"\bflake8\b",
    r"\bpylint\b",
    r"\bmypy\b",
    r"\bpyright\b",
    r"\bblack\b.*--check",
    # JavaScript / TypeScript
    r"\beslint\b",
    r"\btsc\b.*--noEmit|--noEmit",
    r"\bbiome\b",
    # Go
    r"golangci-lint",
    r"\bgo vet\b|go\s+vet\b",
    r"staticcheck",
    # Rust
    r"cargo clippy|cargo\s+clippy",
    r"cargo fmt|cargo\s+fmt",
    # PHP
    r"\bphpstan\b",
    r"\bpsalm\b",
    r"php-cs-fixer",
    # C#
    r"dotnet format|dotnet\s+format",
    r"EnableNETAnalyzers",
    # C/C++
    r"\bcppcheck\b",
    r"clang-tidy",
    # Universal
    r"lint|Lint|LINT",
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

    if any(re.search(pat, code) for pat in LINT_PATTERNS):
        return 0

    return fail(
        "CI/CD pipeline has no linting or static analysis step — "
        "add a linter appropriate for the project language"
    )


if __name__ == "__main__":
    sys.exit(main())
