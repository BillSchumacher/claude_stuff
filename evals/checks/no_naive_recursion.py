"""Fail if a recursive function lacks memoization when it has overlapping subproblems.

Detects: recursive call to the same function without @cache, @lru_cache, or a
manual memo dict.  Language-aware: checks Python and JS/TS with appropriate
patterns, using brace-counting for JS function scope.
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


def _extract_brace_body(code: str, open_pos: int) -> str:
    """Return text between { at open_pos and its matching }, exclusive."""
    depth = 1
    i = open_pos + 1
    while i < len(code) and depth > 0:
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
        i += 1
    return code[open_pos + 1 : i - 1]


def _js_function_body(code: str, func_name: str) -> str:
    """Extract body of a JS function declaration or arrow function."""
    patterns = [
        rf"function\s+{re.escape(func_name)}\s*\([^)]*\)\s*\{{",
        rf"(?:const|let|var)\s+{re.escape(func_name)}\s*=\s*(?:\([^)]*\)|\w+)\s*=>\s*\{{",
    ]
    for pat in patterns:
        m = re.search(pat, code)
        if m:
            brace_pos = code.rfind("{", m.start(), m.end())
            if brace_pos != -1:
                return _extract_brace_body(code, brace_pos)
    return ""


def check_python(code: str) -> str | None:
    for fname in re.findall(r"def\s+(\w+)\s*\(", code):
        parts = code.split(f"def {fname}")
        if len(parts) < 2:
            continue
        # Approximate body: up to next top-level def
        body = parts[1].split("\ndef ")[0]
        if re.search(rf"\b{fname}\s*\(", body):
            if not re.search(
                r"@cache|@lru_cache|memo|_cache|functools\.cache", code,
            ):
                return (
                    f"Recursive function '{fname}' without memoization — "
                    "use @functools.cache or a manual memo dict"
                )
    return None


def check_js(code: str) -> str | None:
    decl_funcs = re.findall(r"function\s+(\w+)\s*\(", code)
    arrow_funcs = re.findall(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|\w+)\s*=>", code,
    )
    for fname in set(decl_funcs + arrow_funcs):
        body = _js_function_body(code, fname)
        if body and re.search(rf"\b{fname}\s*\(", body):
            if not re.search(r"memo|cache|Map\(\)|new Map|WeakMap", code):
                return f"Recursive function '{fname}' without memoization"
    return None


def main() -> int:
    stdin = sys.stdin.read()
    lang = detect_target_language() or "python"

    if lang == "python":
        code = get_all_code(stdin, require_language_tag=True)
        if code.strip():
            msg = check_python(code)
            if msg:
                return fail(msg)
    elif lang in ("javascript", "typescript"):
        code = get_all_code_c_style(
            stdin,
            languages=("javascript", "js", "typescript", "ts"),
            require_language_tag=True,
        )
        if code.strip():
            msg = check_js(code)
            if msg:
                return fail(msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
