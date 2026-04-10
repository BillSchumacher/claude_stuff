"""Fail if JavaScript/TypeScript code uses Array.includes / indexOf for membership inside a loop.

Passes if the code uses Set.has or Map.has for membership, or has no loop-based
membership test at all.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(
        sys.stdin.read(),
        languages=("javascript", "js", "typescript", "ts"),
    )
    if not code:
        return fail("No code found")

    # Look for a `for` construct followed by .includes( or .indexOf( in the body.
    # Since we don't have a real parser, we look for any for / while that is
    # followed (within ~500 chars) by .includes(.
    for_block = re.search(
        r"\b(for|while)\s*\([^)]*\)\s*\{[^}]{0,500}\.includes\s*\(",
        code,
        re.DOTALL,
    )
    if for_block:
        return fail(
            f"Array.includes inside a {for_block.group(1)} loop is O(n·m); "
            "convert the right-hand side to a Set once and use Set.has (O(1))"
        )

    for_of_block = re.search(
        r"\bfor\s*\(\s*(?:const|let|var)\s+\w+\s+of[^)]*\)\s*\{[^}]{0,500}\.includes\s*\(",
        code,
        re.DOTALL,
    )
    if for_of_block:
        return fail(
            "Array.includes inside a for-of loop is O(n·m); "
            "convert the right-hand side to a Set and use Set.has (O(1))"
        )

    # .indexOf(x) !== -1 as a membership test inside a loop
    indexof_block = re.search(
        r"\b(for|while)\s*\([^)]*\)\s*\{[^}]{0,500}\.indexOf\s*\([^)]*\)\s*!==?\s*-1",
        code,
        re.DOTALL,
    )
    if indexof_block:
        return fail("Array.indexOf !== -1 membership test inside a loop; use a Set")

    return 0


if __name__ == "__main__":
    sys.exit(main())
