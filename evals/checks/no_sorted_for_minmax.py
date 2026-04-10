"""Fail if code sorts a collection just to get the min or max element.

- Python: sorted(xs)[0] -> min(xs); sorted(xs)[-1] -> max(xs)
- Go: sort.Slice/Sort then [0] -> iterate to find min
- JS/TS: .sort(...)[0] -> reduce / Math.min
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import (
    get_all_code,
    get_all_code_c_style,
    detect_target_language,
    fail,
)


def check_python(code: str) -> str | None:
    if re.search(r"sorted\s*\([^)]*\)\s*\[\s*0\s*\]", code):
        return "sorted(...)[0] is O(n log n); use min(...) which is O(n)"
    if re.search(r"sorted\s*\([^)]*\)\s*\[\s*-1\s*\]", code):
        return "sorted(...)[-1] is O(n log n); use max(...) which is O(n)"
    return None


def check_go(code: str) -> str | None:
    if re.search(r"sort\.\w+\s*\(", code) and re.search(r"\[\s*0\s*\]", code):
        return "sort.Slice/Sort then [0] is O(n log n); iterate to find min in O(n)"
    return None


def check_js(code: str) -> str | None:
    if re.search(r"\.sort\s*\(", code) and re.search(r"\[\s*0\s*\]", code):
        if not re.search(r"Math\.min|Math\.max|\.reduce\s*\(", code):
            return ".sort(...)[0] is O(n log n); use reduce/Math.min which is O(n)"
    return None


LANG_CHECKERS = {
    "python": (
        lambda stdin: get_all_code(stdin, require_language_tag=True),
        check_python,
    ),
    "go": (
        lambda stdin: get_all_code_c_style(
            stdin, languages=("go", "golang"), require_language_tag=True,
        ),
        check_go,
    ),
    "javascript": (
        lambda stdin: get_all_code_c_style(
            stdin, languages=("javascript", "js", "typescript", "ts"),
            require_language_tag=True,
        ),
        check_js,
    ),
    "typescript": (
        lambda stdin: get_all_code_c_style(
            stdin, languages=("javascript", "js", "typescript", "ts"),
            require_language_tag=True,
        ),
        check_js,
    ),
}


def main() -> int:
    stdin = sys.stdin.read()
    lang = detect_target_language() or "python"

    extractor, checker = LANG_CHECKERS.get(
        lang, LANG_CHECKERS["python"],
    )
    code = extractor(stdin)
    if code.strip():
        msg = checker(code)
        if msg:
            return fail(msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
