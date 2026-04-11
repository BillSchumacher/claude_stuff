"""Fail if code serves files from user input without path traversal protection.

Multi-language: Python open/send_file, Go http.ServeFile, JS res.sendFile,
PHP file_get_contents/readfile.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

SAFE_PATTERNS = [
    # Python
    r"send_from_directory\s*\(",
    r"secure_filename\s*\(",
    # Universal path validation
    r"os\.path\.realpath|os\.path\.abspath|\.resolve\s*\(",
    r'"\.\.".*in\b|"\.\.".*not in\b|\.\.\s+in\b',
    r"os\.path\.commonpath|\.startswith\s*\(",
    # Go
    r"filepath\.Clean\s*\(",
    r"filepath\.Rel\s*\(",
    r"strings\.Contains\s*\([^)]*\.\.",
    r"http\.Dir\s*\(",
    # JS
    r"path\.resolve\s*\(",
    r"path\.normalize\s*\(",
    r"\.includes\s*\(\s*['\"]\.\.['\"]\s*\)",
    # PHP
    r"realpath\s*\(",
    r"basename\s*\(",
    r"str_contains\s*\([^)]*\.\.",
    r"strpos\s*\([^)]*\.\.",
]

FILE_SERVE_PATTERNS = [
    r"open\s*\(",
    r"send_file\s*\(",
    r"send_from_directory\s*\(",
    r"http\.ServeFile\s*\(",
    r"http\.ServeContent\s*\(",
    r"res\.sendFile\s*\(",
    r"res\.download\s*\(",
    r"file_get_contents\s*\(",
    r"readfile\s*\(",
    r"fopen\s*\(",
]


def main() -> int:
    stdin = sys.stdin.read()
    code = get_all_code(
        stdin,
        languages=(
            "python", "py", "go", "golang", "javascript", "js",
            "typescript", "ts", "php", "csharp", "cs",
        ),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No code found")

    if not any(re.search(pat, code) for pat in FILE_SERVE_PATTERNS):
        return 0  # No file serving detected

    if any(re.search(pat, code) for pat in SAFE_PATTERNS):
        return 0

    return fail(
        "File served from user input without path traversal protection — "
        "validate the resolved path stays within the base directory"
    )


if __name__ == "__main__":
    sys.exit(main())
