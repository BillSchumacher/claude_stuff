"""Fail if C# CI doesn't chain --no-restore and --no-build flags.

The correct pattern: dotnet restore → dotnet build --no-restore →
dotnet test --no-build. Without chaining, each step redundantly
re-downloads packages or re-compiles.
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

    has_build = re.search(r"dotnet build\b", code)
    has_test = re.search(r"dotnet test\b", code)
    if not has_build or not has_test:
        return 0  # Incomplete workflow, N/A

    has_no_restore = re.search(r"--no-restore", code)
    has_no_build = re.search(r"--no-build", code)

    if has_no_restore and has_no_build:
        return 0

    missing = []
    if not has_no_restore:
        missing.append("--no-restore on build")
    if not has_no_build:
        missing.append("--no-build on test")

    return fail(
        f".NET CI missing {' and '.join(missing)} — "
        "chain restore → build --no-restore → test --no-build "
        "to avoid redundant work"
    )


if __name__ == "__main__":
    sys.exit(main())
