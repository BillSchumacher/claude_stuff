"""Fail if Go code uses string += in a loop instead of strings.Builder / bytes.Buffer.

Go strings are immutable, so += inside a loop is O(n²) in the total output size.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(
        sys.stdin.read(),
        languages=("go", "golang"),
    )
    if not code:
        return fail("No code found")

    # Identify `for ... { ... += ... }` patterns where the accumulator looks string-ish.
    # Go syntax: `for <init>; <cond>; <post> { ... }` or `for range` / `for _, v := range`.
    # We look for `+=` inside a `for { ... }` block, and check that a `string` type
    # is declared or a `strings.Builder` is NOT used nearby.
    for_with_concat = re.search(
        r"\bfor\b[^{]*\{[^}]*?\b(\w+)\s*\+=\s*\w+[^}]*?\}",
        code,
        re.DOTALL,
    )
    if for_with_concat:
        acc = for_with_concat.group(1)
        # Suppress false positive if a strings.Builder / bytes.Buffer was declared
        if re.search(r"strings\.Builder|bytes\.Buffer", code):
            return 0
        # Make sure it's string-typed: look for a preceding `var <acc> string` or
        # `<acc> := ""` or `<acc> = ""`.
        is_string = re.search(
            rf"\b{re.escape(acc)}\s*(?::=|=|var\s+{re.escape(acc)}\s+string\s*=)\s*\"\"?",
            code,
        ) or re.search(
            rf"var\s+{re.escape(acc)}\s+string\b",
            code,
        )
        if is_string:
            return fail(
                f"String concat with += inside a for loop (accumulator: {acc}); "
                "use strings.Builder or bytes.Buffer (Go strings are immutable → O(n²))"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
