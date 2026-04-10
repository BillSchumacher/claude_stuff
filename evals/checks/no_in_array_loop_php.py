"""Fail if PHP code uses in_array() inside a foreach loop for membership testing.

in_array is O(n). For repeated membership on the same list, flip it into a
hash lookup: $lookup = array_flip($list); isset($lookup[$x]).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(sys.stdin.read(), languages=("php",))
    if not code:
        return fail("No code found")

    # in_array( inside a foreach or for block
    loop_with_in_array = re.search(
        r"\b(foreach|for|while)\s*\([^)]*\)\s*\{[^}]{0,500}?\bin_array\s*\(",
        code,
        re.DOTALL,
    )
    if loop_with_in_array:
        # If array_flip or array_intersect is also used, allow it
        if re.search(r"\barray_flip\s*\(|\barray_intersect\s*\(", code):
            return 0
        return fail(
            f"in_array() inside a {loop_with_in_array.group(1)} loop is O(n·m); "
            "use array_flip() + isset() for O(1) lookup, or array_intersect()"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
