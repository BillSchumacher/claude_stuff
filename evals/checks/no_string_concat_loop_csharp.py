"""Fail if C# code uses string += inside a loop instead of StringBuilder.

C# strings are immutable; += copies the accumulator each time → O(n²).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(sys.stdin.read(), languages=("csharp", "cs", "c#"))
    if not code:
        return fail("No code found")

    # Look for += inside a for/foreach/while block where the LHS is a string
    loop_with_concat = re.search(
        r"\b(for|foreach|while)\s*\([^)]*\)\s*\{[^}]{0,500}?\b(\w+)\s*\+=",
        code,
        re.DOTALL,
    )
    if loop_with_concat:
        # If StringBuilder is used anywhere, allow it — the += might be on an int
        if re.search(r"\bStringBuilder\b", code):
            return 0
        # Check if the variable was declared as string or assigned ""
        acc = loop_with_concat.group(2)
        is_string = bool(
            re.search(rf"\bstring\s+{re.escape(acc)}\b", code)
            or re.search(rf'{re.escape(acc)}\s*=\s*""', code)
        )
        if is_string:
            return fail(
                f"string += inside a {loop_with_concat.group(1)} loop (O(n²)); "
                "use StringBuilder instead"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
