"""Fail if code deduplicates via nested loop / repeated linear contains instead of a hash set.

Works across languages: detects nested for with ==, .contains() in a loop,
.includes() in a loop, in_array() in a loop, or Vec::contains() in a loop.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, fail


def main() -> int:
    stdin = sys.stdin.read()
    # Try all language families
    code = get_all_code(stdin, strip_docs=True)
    code += "\n" + get_all_code_c_style(
        stdin,
        languages=("go", "golang", "rust", "rs", "csharp", "cs", "c#",
                    "javascript", "js", "typescript", "ts", "php",
                    "cpp", "c++", "c"),
    )
    if not code.strip():
        return fail("No code found")

    # Nested for with == (C-style)
    if re.search(r"\bfor\b[^{]*\{[^}]*?\bfor\b[^{]*\{[^}]{0,300}==", code, re.DOTALL):
        return fail("Nested loops with == for dedup is O(n²); use a hash set")

    # .contains() inside a for/foreach/while (C#, Rust, Java)
    if re.search(r"\b(for|foreach|while)\b[^{]*\{[^}]{0,500}\.contains\s*\(", code, re.DOTALL | re.IGNORECASE):
        # Allow if HashSet/HashMap is also used
        if not re.search(r"HashSet|HashMap|hash_set|BTreeSet", code, re.IGNORECASE):
            return fail(".contains() inside a loop is O(n²); use a HashSet for O(1) lookup")

    # in_array inside foreach (PHP)
    if re.search(r"\bforeach\b[^{]*\{[^}]{0,500}\bin_array\s*\(", code, re.DOTALL):
        if not re.search(r"array_flip|array_unique|array_intersect", code):
            return fail("in_array() inside foreach is O(n²); use array_flip + isset or array_unique")

    # .includes inside for/forEach (JS/TS)
    if re.search(r"\b(for|forEach)\b[^{]*[{(][^}]{0,500}\.includes\s*\(", code, re.DOTALL):
        if not re.search(r"new\s+Set\s*\(", code):
            return fail(".includes() inside a loop is O(n²); use a Set for O(1) lookup")

    return 0


if __name__ == "__main__":
    sys.exit(main())
