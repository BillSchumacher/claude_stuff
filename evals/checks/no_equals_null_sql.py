"""Fail if SQL uses = NULL or != NULL instead of IS NULL / IS NOT NULL.

= NULL always evaluates to UNKNOWN (not TRUE), which is a common bug.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("sql", "plpgsql", "tsql", "plsql", "mysql"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return 0  # No SQL code found

    # Strip SQL comments
    code = re.sub(r"--[^\n]*", "", code)
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    # Strip string literals
    code = re.sub(r"'(?:[^'\\]|\\.)*'", "''", code)

    # Check for = NULL (but not IS NULL, IS NOT NULL, := NULL for assignments)
    # Match: column = NULL, foo != NULL, bar <> NULL
    bad = re.search(
        r"(?<!\bIS\s)(?<!\bIS\sNOT\s)(?<!:)\b(\w+)\s*(?:!=|<>|=)\s*NULL\b",
        code,
        re.IGNORECASE,
    )
    if bad:
        return fail(
            f"SQL uses = NULL or != NULL: `{bad.group(0).strip()}` — "
            "use IS NULL / IS NOT NULL instead (= NULL always returns UNKNOWN)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
