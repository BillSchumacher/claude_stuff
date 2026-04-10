"""Fail if Python code uses list.pop(0) or list.insert(0, ...) instead of collections.deque.

These are O(n) per call. For queue-like usage, deque is O(1).
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

    # .pop(0) — O(n) front removal
    match = re.search(r"\.pop\s*\(\s*0\s*\)", code)
    if match:
        return fail(
            f"list.pop(0) is O(n); use collections.deque.popleft() instead "
            f"(found: {match.group(0)})"
        )

    # .insert(0, ...) — O(n) front insertion
    match = re.search(r"\.insert\s*\(\s*0\s*,", code)
    if match:
        return fail(
            f".insert(0, ...) is O(n); use collections.deque.appendleft() instead "
            f"(found: {match.group(0)})"
        )

    # Also flag manual rolling-buffer trim: `if len(x) > N: x = x[1:]` or `x.pop(0)`
    # The pop(0) case is already caught above; catch the slice reassignment form.
    match = re.search(
        r"=\s*\w+\s*\[\s*1\s*:\s*\]",
        code,
    )
    if match and re.search(r"\blen\s*\(\s*\w+\s*\)\s*>\s*\w+", code):
        return fail(
            "Manual rolling-buffer trim via slice reassignment is O(n); "
            "use collections.deque(maxlen=...) instead"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
