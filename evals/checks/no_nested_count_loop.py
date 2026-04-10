"""Fail if Python code calls .count() on a list inside a loop over that list.

Pattern: `for x in cart: if cart.count(x.product_id) >= 5: ...` — O(n²).
Efficient alternative: `Counter(...)` once, then look up counts in O(1).
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

    # Find .count( calls inside a for/while loop body.
    # Heuristic: for or while line followed within 300 chars by .count(
    nested_count = re.search(
        r"\b(for|while)\s+[^\n]*:\s*\n(?:[^\n]*\n){0,15}?[^\n]*\.count\s*\(",
        code,
    )
    if nested_count:
        # If Counter is used, the .count() might be on a different structure — allow it
        if re.search(r"\bCounter\s*\(", code):
            return 0
        return fail(
            "list.count() called inside a loop — O(n²). "
            "Use collections.Counter once before the loop, then look up counts in O(1)."
        )

    # Multiple .count() calls on the same list name — another red flag
    count_calls = re.findall(r"(\w+)\.count\s*\(", code)
    if len(count_calls) >= 3 and len(set(count_calls)) <= 2:
        if not re.search(r"\bCounter\s*\(", code):
            return fail(
                f"Repeated .count() calls on {count_calls[0]!r} — O(n) each. "
                "Use collections.Counter once."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
