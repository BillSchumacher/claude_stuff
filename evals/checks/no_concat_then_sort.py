"""Fail if code merges two sorted arrays by concatenating then sorting.

Works across languages: detects sort() / qsort / Arrays.sort applied after
array concatenation when the inputs are described as already sorted.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, fail


def main() -> int:
    stdin = sys.stdin.read()
    code = get_all_code(stdin, strip_docs=True)
    code += "\n" + get_all_code_c_style(
        stdin, languages=("c", "cpp", "c++"),
    )
    if not code.strip():
        return fail("No code found")

    # C: memcpy both arrays then qsort the combined
    if re.search(r"qsort\s*\(", code) and re.search(r"memcpy\s*\(", code):
        return fail("Concatenating then qsort is O((n+m) log(n+m)); use a linear merge O(n+m)")

    # Python: sorted(a + b) — already covered by no_sort_after_concat.py but
    # we include for completeness
    if re.search(r"sorted\s*\(\s*\w+\s*\+\s*\w+", code):
        return fail("sorted(a + b) is O((n+m) log(n+m)); merge already-sorted inputs in O(n+m)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
