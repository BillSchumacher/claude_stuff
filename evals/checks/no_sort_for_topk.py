"""Fail if Python code uses sorted(...)[:k] for top-k instead of heapq.nlargest/nsmallest.

Passes if the code uses heapq.nlargest, heapq.nsmallest, or a plain min/max
(acceptable for k=1) — or if there's no top-k pattern at all.
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

    # Anti-pattern: sorted(...)[:k] or sorted(...)[-k:] for numeric k or variable k
    bad_top = re.search(
        r"sorted\s*\([^)]*\)\s*\[\s*:\s*\w+\s*\]",
        code,
    )
    bad_bottom = re.search(
        r"sorted\s*\([^)]*\)\s*\[\s*-\w+\s*:\s*\]",
        code,
    )
    if bad_top:
        return fail(f"Top-k via sort slice: {bad_top.group(0)}")
    if bad_bottom:
        return fail(f"Bottom-k via sort slice: {bad_bottom.group(0)}")

    # Positive signal: heapq.nlargest / nsmallest is an acceptable implementation
    if re.search(r"heapq\.n(?:largest|smallest)\s*\(", code):
        return 0
    # min/max are acceptable for k=1 cases
    if re.search(r"\bmin\s*\(|\bmax\s*\(", code):
        return 0
    # If no top-k shape is present at all, we consider it passing by default
    return 0


if __name__ == "__main__":
    sys.exit(main())
