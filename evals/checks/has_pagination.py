"""Check that list/collection API endpoints include pagination.

Looks for pagination parameters (page, limit, offset, cursor, pageToken,
page_size, per_page) in endpoint definitions or query handling.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, detect_target_language, fail

PAGINATION_PATTERNS = [
    r"\bpage_?size\b",
    r"\bper_?page\b",
    r"\bpage_?token\b",
    r"\bnext_?cursor\b",
    r"\bcursor\b",
    r"\blimit\b.*\boffset\b",
    r"\boffset\b.*\blimit\b",
    r"\bpaginate\b",
    r"\bPagination\b",
    r"\bpaginated\b",
    r"\bpage\s*[=:]\s*\d",
    r"[?&]page=",
    r"[?&]limit=",
    r"\bskip\b.*\btake\b",
]


def main() -> int:
    stdin = sys.stdin.read()
    lang = detect_target_language()

    if lang in ("go", "javascript", "typescript", "csharp", "rust", "php", "cpp"):
        code = get_all_code_c_style(
            stdin,
            languages=(
                "go", "golang", "javascript", "js", "typescript", "ts",
                "php", "csharp", "cs", "rust", "rs", "c", "cpp",
            ),
        )
    else:
        code = get_all_code(
            stdin,
            languages=("python", "py"),
            strip_docs=False,
        )

    # Also check raw text for pagination discussion
    text = stdin + "\n" + code

    if not text.strip():
        return fail("No output found")

    for pattern in PAGINATION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return 0

    return fail(
        "No pagination found on list endpoint. "
        "Expected page_size/limit+offset/cursor-based pagination parameters."
    )


if __name__ == "__main__":
    sys.exit(main())
