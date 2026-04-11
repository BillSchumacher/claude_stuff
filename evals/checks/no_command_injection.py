"""Fail if code runs shell commands with user-controlled input.

Multi-language: Python subprocess/os.system, Go exec.Command with shell,
JS child_process.exec, PHP exec/system/shell_exec/passthru.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def _strip_comments(code: str) -> str:
    """Strip comments but preserve string literals."""
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    code = re.sub(r"//[^\n]*", "", code)
    code = re.sub(r"#[^\n]*", "", code)
    return code


def main() -> int:
    stdin = sys.stdin.read()
    code = get_all_code(
        stdin,
        languages=(
            "python", "py", "go", "golang", "javascript", "js",
            "typescript", "ts", "php", "csharp", "cs", "rust", "rs",
            "c", "cpp", "c++",
        ),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No code found")

    code = _strip_comments(code)

    # --- Python ---
    shell_true = re.search(
        r"subprocess\.\w+\([^)]*shell\s*=\s*True", code, re.DOTALL,
    )
    if shell_true:
        snippet = shell_true.group(0)
        if re.search(r'f["\']|["\'].*\+|\.format|%', snippet):
            return fail(
                f"subprocess with shell=True and interpolation: {snippet[:120]}"
            )
        return fail(
            f"subprocess with shell=True (pass list args instead): {snippet[:120]}"
        )

    os_system = re.search(r"os\.system\(([^)]+)\)", code)
    if os_system:
        arg = os_system.group(1)
        if any(c in arg for c in ["+", "f'", 'f"', ".format", "%"]):
            return fail(f"os.system with interpolation: {os_system.group(0)[:120]}")

    if re.search(r"\bos\.popen\(", code):
        return fail("os.popen is unsafe; use subprocess with list args")

    # --- Go ---
    go_shell = re.search(
        r'exec\.Command\s*\(\s*["\'](?:sh|bash|cmd)["\']'
        r'\s*,\s*["\'](?:-c|/c)["\']',
        code,
    )
    if go_shell:
        return fail(
            f"exec.Command with shell -c (pass command and args directly): "
            f"{go_shell.group(0)[:120]}"
        )

    # --- JavaScript / TypeScript ---
    js_exec = re.search(r"child_process\.exec\s*\(", code)
    if js_exec:
        return fail(
            "child_process.exec runs a shell; use execFile or spawn with "
            "array args instead"
        )
    if re.search(r"\.exec\s*\(\s*`", code):
        return fail("exec() with template literal — use execFile with array args")

    # --- PHP ---
    php_shell = re.search(
        r"\b(?:exec|system|shell_exec|passthru|popen)\s*\(\s*\$", code,
    )
    if php_shell:
        return fail(
            f"PHP {php_shell.group(0)[:60]} with variable — use "
            "escapeshellarg() or avoid shell entirely"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
