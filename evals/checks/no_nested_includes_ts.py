"""Fail if TypeScript/JavaScript code uses Array.includes inside a nested iteration.

Pattern: filter products where selectedTags.every(t => product.tags.includes(t)).
That's O(products × selectedTags × productTags). A Set lookup would make the
inner check O(1).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code_c_style, fail


def main() -> int:
    code = get_all_code_c_style(
        sys.stdin.read(),
        languages=("typescript", "ts", "javascript", "js"),
    )
    if not code:
        return fail("No code found")

    # Pattern 1: .filter(...) callback that contains .every / .some / .includes on an array
    # The filter callback is itself a loop (over the outer array), so .includes inside
    # is nested iteration.
    filter_with_includes = re.search(
        r"\.filter\s*\([^)]*?=>\s*[^{]{0,200}\.includes\s*\(",
        code,
        re.DOTALL,
    )
    if filter_with_includes:
        if re.search(r"new\s+Set\s*\(", code):
            # Check the Set is created OUTSIDE the filter callback, not inside it
            # (inside would still be O(n×m) per call)
            set_outside = re.search(
                r"(?:const|let|var)\s+\w+\s*=\s*new\s+Set\s*\([^)]*\)[\s\S]*?\.filter",
                code,
            )
            if set_outside:
                return 0
        return fail(
            "Array.includes inside .filter() callback — O(n × m). "
            "Build a Set once outside the filter and use Set.has (O(1))."
        )

    # Pattern 2: .every / .some with .includes is still nested iteration
    every_with_includes = re.search(
        r"\.every\s*\([^)]*?=>\s*[^{]{0,200}\.includes\s*\(",
        code,
    )
    if every_with_includes:
        if re.search(r"new\s+Set\s*\(", code):
            return 0
        return fail(
            ".every() callback with .includes() — O(n × m). "
            "Convert one side to a Set for O(1) membership."
        )

    # Pattern 3: explicit for loop with nested .includes
    nested_for_includes = re.search(
        r"\bfor\s*\([^)]*\)\s*\{[^}]{0,500}\.includes\s*\(",
        code,
        re.DOTALL,
    )
    if nested_for_includes:
        if not re.search(r"new\s+Set\s*\(", code):
            return fail("for loop with .includes() inside — O(n × m). Use a Set.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
