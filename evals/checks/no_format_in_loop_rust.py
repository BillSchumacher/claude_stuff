"""Fail if Rust code uses format! inside a for loop to build a string.

`format!` allocates a new String each call. In a loop, use `write!` to an
existing String or `push_str` with pre-allocated capacity.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(sys.stdin.read(), languages=("rust", "rs"))
    if not code:
        return fail("No code found")

    # format! inside a for loop body
    for_with_format = re.search(
        r"\bfor\b[^{]*\{[^}]{0,500}?\bformat!\s*\(",
        code,
        re.DOTALL,
    )
    if for_with_format:
        # Allow if write! or push_str is also used (format! might be for something else)
        if re.search(r"\bwrite!\s*\(|\bpush_str\s*\(", code):
            return 0
        return fail(
            "format! inside a for loop allocates a new String each iteration; "
            "use write!(buf, ...) or push_str on a pre-allocated String"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
