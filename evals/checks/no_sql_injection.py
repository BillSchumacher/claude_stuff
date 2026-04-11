"""Fail if SQL queries use string formatting/concatenation instead of parameters.

Multi-language: detects Python f-strings, Go fmt.Sprintf, JS template literals,
PHP interpolation, C# $-strings, Rust format!, C sprintf, and C++ concatenation.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

SQL_KW = r"(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION)"


def _strip_comments(code: str) -> str:
    """Strip comments but preserve string literals (needed to detect SQL injection)."""
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    code = re.sub(r"//[^\n]*", "", code)
    code = re.sub(r"#[^\n]*", "", code)
    return code


BAD_PATTERNS = [
    # Python f-string SQL: f"SELECT ... {var}"
    (rf'f["\'](?:[^"\']*?){SQL_KW}[^"\']*?\{{[^}}]+\}}', "f-string SQL"),
    # Python %-formatted SQL: "SELECT ... %s" % var
    (rf'["\'](?:[^"\']*?){SQL_KW}[^"\']*?["\'](?:\s*%\s*)', "%-formatted SQL"),
    # .format() SQL: "SELECT ... {}".format(var)
    (rf'["\'](?:[^"\']*?){SQL_KW}[^"\']*?\{{\}}[^"\']*?["\']\s*\.format\(',
     ".format() SQL"),
    # Go fmt.Sprintf SQL: fmt.Sprintf("SELECT ... %s", var)
    (rf'fmt\.Sprintf\s*\(\s*["\'][^"\']*?{SQL_KW}', "Go fmt.Sprintf SQL"),
    # JS/TS template literal SQL: `SELECT ... ${var}`
    (rf'`[^`]*?{SQL_KW}[^`]*?\$\{{', "template literal SQL"),
    # PHP variable interpolation: "SELECT ... $var" (PHP vars start with letter/_)
    (rf'"[^"]*?{SQL_KW}[^"]*?\$[a-zA-Z_]\w*', "PHP interpolated SQL"),
    # PHP concatenation: "SELECT ..." . $var
    (rf'["\'][^"\']*?{SQL_KW}[^"\']*?["\']\s*\.(?!\w)', "PHP concatenated SQL"),
    # C# string interpolation: $"SELECT ... {var}"
    (rf'\$"[^"]*?{SQL_KW}[^"]*?\{{', "C# interpolated SQL"),
    # Rust format! SQL: format!("SELECT ... {}", var)
    (rf'format!\s*\(\s*"[^"]*?{SQL_KW}', "Rust format! SQL"),
    # C sprintf SQL: sprintf(buf, "SELECT ... %s", var)
    (rf'(?:sprintf|snprintf)\s*\([^,]+,\s*"[^"]*?{SQL_KW}', "C sprintf SQL"),
    # Concatenated SQL (universal: Python/JS/C#/C++/Go)
    (rf'["\'](?:[^"\']*?){SQL_KW}[^"\']*?["\']\s*\+', "concatenated SQL"),
    # C++ stream SQL: sql << "SELECT ..."
    (rf'<<\s*["\'][^"\']*?{SQL_KW}', "C++ stream-concatenated SQL"),
]


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

    for pattern, label in BAD_PATTERNS:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return fail(f"Detected {label}: {match.group(0)[:100]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
