"""Check that API errors use a standard format (RFC 9457 problem+json or consistent shape).

Looks for: application/problem+json, problem detail fields (type, title, status, detail),
or a consistent error response structure.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, detect_target_language, fail

ERROR_FORMAT_PATTERNS = [
    # RFC 9457 problem+json
    r"application/problem\+json",
    r"problem\+json",
    # Problem detail fields together
    r'"type".*"title".*"status"',
    r'"title".*"status".*"detail"',
    # Common structured error patterns
    r"ProblemDetail",
    r"problem_detail",
    r"ErrorResponse",
    r"error_response",
    r"ApiError",
    r"HttpProblem",
    # OpenAPI error schema
    r"responses:[\s\S]*?4\d\d:[\s\S]*?schema",
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
                "yaml", "yml", "json",
            ),
        )
    else:
        code = get_all_code(
            stdin,
            languages=("python", "py", "yaml", "yml", "json"),
            strip_docs=False,
        )

    text = stdin + "\n" + code

    if not text.strip():
        return fail("No output found")

    for pattern in ERROR_FORMAT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return 0

    return fail(
        "No standard error format found. "
        "Expected RFC 9457 application/problem+json or a consistent "
        "error response structure (type, title, status, detail)."
    )


if __name__ == "__main__":
    sys.exit(main())
