"""Fail if JavaScript/TypeScript uses Array.shift() inside a loop.

.shift() is O(n) because it re-indexes all remaining elements.
Inside a loop this gives O(n^2). Use a queue index, reverse+pop, or a deque.
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
        require_language_tag=True,
    )
    if not code.strip():
        return 0  # No JS/TS code

    # Look for .shift() inside while/for loops
    # Pattern: while(...) { ... .shift() ... } or for(...) { ... .shift() ... }
    loop_bodies = re.findall(
        r"(?:while|for)\s*\([^)]*\)\s*\{([\s\S]*?)\}",
        code,
    )

    for body in loop_bodies:
        if re.search(r"\.shift\s*\(\s*\)", body):
            return fail(
                "Array.shift() inside a loop is O(n) per call (re-indexes all elements). "
                "Use a queue index, reverse()+pop(), or a proper deque instead."
            )

    # Also check while (arr.length) { arr.shift() } pattern
    if re.search(
        r"while\s*\(\s*\w+\.length\s*\)\s*\{[\s\S]*?\.shift\s*\(",
        code,
    ):
        return fail(
            "Array.shift() in a while(arr.length) loop is O(n^2) total. "
            "Use a queue index or reverse()+pop() instead."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
