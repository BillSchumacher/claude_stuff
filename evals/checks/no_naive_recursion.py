"""Fail if a recursive function lacks memoization when it has overlapping subproblems.

Detects: recursive call to the same function without @cache, @lru_cache, or a
manual memo dict.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, fail


def main() -> int:
    stdin = sys.stdin.read()
    code = get_all_code(stdin) + "\n" + get_all_code_c_style(
        stdin, languages=("javascript", "js", "typescript", "ts", "go", "golang",
                          "rust", "rs", "cpp", "c++", "c", "csharp", "cs", "php"),
    )
    if not code.strip():
        return fail("No code found")

    # Find function definitions and check if they call themselves
    # Python: def foo(...): ... foo(
    py_funcs = re.findall(r"def\s+(\w+)\s*\(", code)
    for fname in py_funcs:
        # Check if function calls itself
        if re.search(rf"\b{fname}\s*\(", code.split(f"def {fname}")[1] if f"def {fname}" in code else ""):
            # Check for memoization
            if not re.search(r"@cache|@lru_cache|memo|_cache|functools\.cache", code):
                return fail(
                    f"Recursive function '{fname}' without memoization — "
                    "use @functools.cache or a manual memo dict"
                )

    # JS/TS: function foo(...) { ... foo(
    js_funcs = re.findall(r"function\s+(\w+)\s*\(", code)
    for fname in js_funcs:
        if re.search(rf"\b{fname}\s*\(", code.split(f"function {fname}")[1] if f"function {fname}" in code else ""):
            if not re.search(r"memo|cache|Map\(\)|WeakMap", code):
                return fail(f"Recursive function '{fname}' without memoization")

    return 0


if __name__ == "__main__":
    sys.exit(main())
