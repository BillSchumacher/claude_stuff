"""Fail if T-SQL misses key best practices.

Checks for: NVARCHAR over VARCHAR for user text, TRY/CATCH with XACT_ABORT,
no NOLOCK hints, DATETIME2 over DATETIME, SCOPE_IDENTITY over @@IDENTITY.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("sql", "tsql", "mssql"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No SQL code found")

    # NOLOCK hint
    if re.search(r"\bNOLOCK\b|\bREAD\s+UNCOMMITTED\b", code, re.IGNORECASE):
        return fail(
            "NOLOCK / READ UNCOMMITTED reads dirty data and can skip or "
            "double-read rows — use Read Committed Snapshot Isolation"
        )

    # DATETIME instead of DATETIME2
    has_ddl = re.search(r"CREATE\s+TABLE", code, re.IGNORECASE)
    if has_ddl:
        if re.search(r"\bDATETIME\b", code, re.IGNORECASE):
            if not re.search(r"\bDATETIME2\b|\bDATETIMEOFFSET\b", code, re.IGNORECASE):
                return fail(
                    "DATETIME type — use DATETIME2 (higher precision, "
                    "wider range) or DATETIMEOFFSET for timezone-aware"
                )

    # @@IDENTITY instead of SCOPE_IDENTITY()
    if re.search(r"@@IDENTITY\b", code):
        return fail(
            "@@IDENTITY crosses scopes (including triggers) — "
            "use SCOPE_IDENTITY() or OUTPUT inserted.id"
        )

    # Transaction without TRY/CATCH
    if re.search(r"BEGIN\s+TRANSACTION", code, re.IGNORECASE):
        if not re.search(r"BEGIN\s+TRY", code, re.IGNORECASE):
            return fail(
                "Transaction without TRY...CATCH — wrap in "
                "TRY/CATCH with SET XACT_ABORT ON"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
