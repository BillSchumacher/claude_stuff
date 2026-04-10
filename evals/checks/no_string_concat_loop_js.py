"""Fail if JavaScript code builds a string with += inside a loop instead of Array.join.

While V8 ConsStrings mitigate worst-case, join is still preferred for
predictable O(n) behavior and avoids flattening cost.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(
        sys.stdin.read(),
        languages=("javascript", "js"),
    )
    if not code:
        return fail("No code found")

    # += inside a for/forEach/for-of/while where the LHS looks like a string accumulator
    loop_with_concat = re.search(
        r"\b(for|while)\s*\([^)]*\)\s*\{[^}]{0,500}?\b(\w+)\s*\+=\s*[`'\"]",
        code,
        re.DOTALL,
    )
    if loop_with_concat:
        if re.search(r"\.join\s*\(", code):
            return 0
        return fail(
            f"String += inside a {loop_with_concat.group(1)} loop; "
            "use Array.push + .join('') for predictable O(n)"
        )

    # forEach with += on a string
    foreach_concat = re.search(
        r"\.forEach\s*\([^)]*=>[^}]{0,300}\b(\w+)\s*\+=\s*[`'\"]",
        code,
        re.DOTALL,
    )
    if foreach_concat:
        if re.search(r"\.join\s*\(", code):
            return 0
        return fail("String += inside forEach; use .map() + .join('')")

    return 0


if __name__ == "__main__":
    sys.exit(main())
