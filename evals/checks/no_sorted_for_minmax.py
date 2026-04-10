"""Fail if code uses sorted(xs)[0] or sorted(xs)[-1] instead of min(xs) / max(xs).

sorted() is O(n log n); min/max are O(n).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    if re.search(r"sorted\s*\([^)]*\)\s*\[\s*0\s*\]", code):
        return fail("sorted(...)[0] is O(n log n); use min(...) which is O(n)")

    if re.search(r"sorted\s*\([^)]*\)\s*\[\s*-1\s*\]", code):
        return fail("sorted(...)[-1] is O(n log n); use max(...) which is O(n)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
