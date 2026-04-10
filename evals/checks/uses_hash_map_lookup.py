"""Fail if C++ code uses a vector/list for key lookup instead of unordered_map/map.

For frequent get-by-key, a hash map (unordered_map) is O(1); linear scan of a
vector of pairs is O(n).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(
        sys.stdin.read(),
        languages=("cpp", "c++", "cxx"),
    )
    if not code:
        return fail("No code found")

    # Positive: unordered_map or map used
    if re.search(r"std::unordered_map|std::map", code):
        return 0

    # Negative: vector of pairs with a linear find
    has_vector_pair = re.search(r"std::vector\s*<\s*std::pair", code)
    has_linear_find = re.search(r"\bstd::find|for\s*\(", code)
    if has_vector_pair and has_linear_find:
        return fail(
            "Using vector<pair> with linear scan for key lookup — O(n). "
            "Use std::unordered_map for O(1) average lookup."
        )

    # If neither positive nor negative pattern, pass by default
    return 0


if __name__ == "__main__":
    sys.exit(main())
