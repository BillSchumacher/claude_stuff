"""Fail if C++ code uses range-for without reference (copies each element).

`for (auto x : container)` copies each element. Use `for (const auto& x : ...)`.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(sys.stdin.read(), languages=("cpp", "c++", "cxx"))
    if not code:
        return fail("No code found")

    # `for (auto x :` or `for (auto [a, b] :` without & — copies every element
    bad = re.search(r"\bfor\s*\(\s*auto\s+(?!&)\w+\s*:", code)
    if bad:
        return fail(
            f"Range-for copies each element: {bad.group(0).strip()} — "
            "use `for (const auto& x : ...)` to avoid the copy"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
