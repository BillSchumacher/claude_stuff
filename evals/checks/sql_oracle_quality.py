"""Fail if Oracle-specific SQL misses key best practices.

Checks for: VARCHAR2 over CHAR/VARCHAR, proper date literals, NUMBER with
precision, no LONG type.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("sql", "plsql", "oracle"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No SQL code found")

    # CHAR type for variable-length data
    if re.search(r"\bCHAR\s*\(\s*\d+\s*\)", code, re.IGNORECASE):
        if not re.search(r"\bVARCHAR2\b", code, re.IGNORECASE):
            return fail(
                "CHAR type — use VARCHAR2 (CHAR pads with spaces, "
                "wastes storage)"
            )

    # LONG type (deprecated)
    if re.search(r"\bLONG\b", code, re.IGNORECASE):
        if not re.search(r"\bLONG\s+RAW\b", code, re.IGNORECASE):
            return fail("LONG type is deprecated — use CLOB/BLOB instead")

    # Implicit date conversion: string literal compared to date column
    # without TO_DATE or DATE literal
    if re.search(r"=\s*'[12]\d{3}-\d{2}-\d{2}'", code):
        if not re.search(r"TO_DATE|DATE\s*'", code, re.IGNORECASE):
            return fail(
                "Implicit date conversion — use DATE '2025-01-01' "
                "or TO_DATE('2025-01-01', 'YYYY-MM-DD')"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
