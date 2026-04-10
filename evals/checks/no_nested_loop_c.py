"""Fail if C code finds duplicates via a nested for loop with == comparison.

Nested loop dedup is O(n²). For integer arrays, sort first (O(n log n)) and
scan adjacent pairs, or use a hash set.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(sys.stdin.read(), languages=("c",))
    if not code:
        return fail("No code found")

    # Two nested for loops with an equality test on array elements:
    # for (int i ...) { for (int j ...) { if (arr[i] == arr[j]) ... } }
    nested = re.search(
        r"\bfor\s*\([^)]*\)\s*\{[^}]*?\bfor\s*\([^)]*\)\s*\{[^}]{0,300}==",
        code,
        re.DOTALL,
    )
    if nested:
        # If qsort or a hash table is also used, this might be acceptable
        if re.search(r"\bqsort\s*\(|\bhash|\bhtable|\buthash", code, re.IGNORECASE):
            return 0
        return fail(
            "Nested for loops with == comparison is O(n²); "
            "sort first with qsort (O(n log n)) and scan adjacent, or use a hash table"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
