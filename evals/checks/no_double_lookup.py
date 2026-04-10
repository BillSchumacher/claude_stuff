"""Fail if code checks membership then accesses a dict/map separately (two lookups).

Detects: `if k in d: v = d[k]` when `v = d.get(k)` or `v, ok = m[k]` would do.
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

    # Python: if k in d: ... d[k]
    pattern = re.search(
        r"if\s+(\w+)\s+in\s+(\w+)\s*:[^\n]*\n[^\n]*\2\s*\[\s*\1\s*\]",
        code,
    )
    if pattern:
        # Allow if .get() or .setdefault() is also used
        if not re.search(r"\.get\s*\(|\.setdefault\s*\(", code):
            return fail(
                f"Two lookups: `if {pattern.group(1)} in {pattern.group(2)}: ... "
                f"{pattern.group(2)}[{pattern.group(1)}]` — use .get(key, default) instead"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
