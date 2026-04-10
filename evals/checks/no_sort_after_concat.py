"""Fail if Python code merges multiple sorted lists by concatenating then sorting.

Correct pattern: `heapq.merge(a, b, c)` — O(n log k) for k lists.
Bad pattern: `sorted(a + b + c)` or `(a + b + c).sort()` — O(n log n) and builds
an intermediate list of all elements.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    # Pattern 1: sorted(a + b + ...) — sorted applied to a list concatenation
    bad_sorted_concat = re.search(
        r"sorted\s*\(\s*\w+(?:\s*\+\s*\w+){1,}",
        code,
    )
    if bad_sorted_concat:
        return fail(
            f"sorted(...) applied to a list concatenation (O(n log n)); "
            f"use heapq.merge for O(n log k) merge of k sorted lists. "
            f"Found: {bad_sorted_concat.group(0)}"
        )

    # Pattern 2: (a + b).sort() — concatenate then in-place sort
    bad_concat_sort = re.search(
        r"\(\s*\w+(?:\s*\+\s*\w+){1,}\s*\)\s*\.sort\s*\(",
        code,
    )
    if bad_concat_sort:
        return fail(
            f"List concatenation then .sort() (O(n log n)); use heapq.merge. "
            f"Found: {bad_concat_sort.group(0)}"
        )

    # Pattern 3: assign concat to a variable then sort it
    # `merged = a + b + c; merged.sort()`  OR  `sorted(merged)` where merged was assigned from a concat
    assigns = re.finditer(
        r"(\w+)\s*=\s*\w+(?:\s*\+\s*\w+){1,}\s*$",
        code,
        re.MULTILINE,
    )
    for m in assigns:
        name = m.group(1)
        # Look for `sorted(name)` or `name.sort()` nearby
        if re.search(rf"sorted\s*\(\s*{re.escape(name)}\s*[),]", code) or re.search(
            rf"\b{re.escape(name)}\.sort\s*\(", code
        ):
            return fail(
                f"Variable {name!r} is a list concatenation then sorted "
                "(O(n log n)); use heapq.merge for O(n log k)."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
