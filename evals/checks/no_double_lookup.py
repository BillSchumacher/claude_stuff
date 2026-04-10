"""Fail if code checks membership then accesses a dict/map separately (two lookups).

- Python: `if k in d: v = d[k]` -> `v = d.get(k)` or walrus operator
- PHP: `isset($d[$k])` then `$d[$k]` -> `$d[$k] ?? default` or `??=`
- Go: `if _, ok := m[k]; ok { m[k] }` -> use the value from the first access
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
    pattern = re.search(
        r"if\s+(\w+)\s+in\s+(\w+)\s*:[^\n]*\n[^\n]*\2\s*\[\s*\1\s*\]",
        code,
    )
    if pattern:
        if not re.search(r"\.get\s*\(|\.setdefault\s*\(", code):
            return (
                f"Two lookups: `if {pattern.group(1)} in {pattern.group(2)}: ... "
                f"{pattern.group(2)}[{pattern.group(1)}]` — use .get(key, default) instead"
            )
    return None


def check_php(code: str) -> str | None:
    # isset($d[$k]) or array_key_exists($k, $d) followed by $d[$k] on next lines
    pattern = re.search(
        r"(?:isset\s*\(\s*(\$\w+)\s*\[|array_key_exists\s*\([^,]+,\s*(\$\w+)\s*\))"
        r"[^\n]*\n[^\n]*(?:\1|\2)\s*\[",
        code,
    )
    if pattern:
        if not re.search(r"\?\?[=\s]", code):
            return (
                "Two lookups: isset/array_key_exists then separate access — "
                "use ?? (null coalescing) or ??= instead"
            )
    return None


def check_go(code: str) -> str | None:
    # if _, ok := m[k]; ok { ... m[k] } — should use the value from first access
    pattern = re.search(
        r"if\s+_\s*,\s*ok\s*:=\s*(\w+)\[(\w+)\]\s*;[^\n]*\n[^\n]*\1\[\2\]",
        code,
    )
    if pattern:
        return (
            "Two lookups: comma-ok then separate access — "
            "use `if v, ok := m[k]; ok { /* use v */ }` instead"
        )
    return None


LANG_CHECKERS = {
    "python": (
        lambda stdin: get_all_code(stdin, require_language_tag=True),
        check_python,
    ),
    "php": (
        lambda stdin: get_all_code_c_style(
            stdin, languages=("php",), require_language_tag=True,
        ),
        check_php,
    ),
    "go": (
        lambda stdin: get_all_code_c_style(
            stdin, languages=("go", "golang"), require_language_tag=True,
        ),
        check_go,
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
