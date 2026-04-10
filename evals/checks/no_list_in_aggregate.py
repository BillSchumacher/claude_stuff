"""Fail if a list comprehension is passed to an aggregating function that accepts generators.

Detects: sum([...]), any([...]), all([...]), max([...]), min([...]), ''.join([...])
when a generator expression would avoid materializing the list.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    pattern = re.search(
        r"\b(sum|any|all|max|min)\s*\(\s*\[",
        code,
    )
    if pattern:
        return fail(
            f"{pattern.group(1)}([...]) materializes a list; "
            f"use {pattern.group(1)}(... for ...) generator expression instead"
        )

    join_pattern = re.search(r"\.join\s*\(\s*\[", code)
    if join_pattern:
        return fail("''.join([...]) materializes a list; use ''.join(... for ...) instead")

    return 0


if __name__ == "__main__":
    sys.exit(main())
