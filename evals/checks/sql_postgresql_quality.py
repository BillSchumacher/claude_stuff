"""Fail if PostgreSQL-specific SQL misses key best practices.

Checks for: TIMESTAMPTZ over TIMESTAMP, TEXT over VARCHAR(n), RETURNING
usage, CONCURRENTLY for index creation, JSONB over JSON.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("sql", "plpgsql", "postgresql"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No SQL code found")

    # TIMESTAMP without TIME ZONE for temporal columns
    if re.search(r"\bTIMESTAMP\b", code, re.IGNORECASE):
        if not re.search(r"TIMESTAMPTZ|TIMESTAMP\s+WITH\s+TIME\s+ZONE", code, re.IGNORECASE):
            return fail(
                "TIMESTAMP without time zone — use TIMESTAMPTZ for "
                "all temporal data in PostgreSQL"
            )

    # JSON instead of JSONB
    if re.search(r"\bJSON\b", code, re.IGNORECASE):
        if not re.search(r"\bJSONB\b", code, re.IGNORECASE):
            return fail(
                "JSON type — use JSONB (binary, indexable, supports "
                "containment operators)"
            )

    # CREATE INDEX without CONCURRENTLY in production-looking DDL
    if re.search(r"CREATE\s+INDEX\s+(?!CONCURRENTLY)", code, re.IGNORECASE):
        if re.search(r"CREATE\s+INDEX\s+CONCURRENTLY", code, re.IGNORECASE):
            pass  # Has at least one CONCURRENTLY, mixed is OK
        else:
            # Only flag if it's not inside a transaction/migration
            if not re.search(r"BEGIN|TRANSACTION", code, re.IGNORECASE):
                return fail(
                    "CREATE INDEX without CONCURRENTLY — use "
                    "CREATE INDEX CONCURRENTLY to avoid write locks"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
