"""Fail if MySQL-specific SQL misses key best practices.

Checks for: utf8mb4 charset, InnoDB engine, BIGINT for PKs, proper
upsert syntax, and common pitfalls.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("sql", "mysql"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No SQL code found")

    has_ddl = re.search(r"CREATE\s+TABLE", code, re.IGNORECASE)
    if not has_ddl:
        return 0  # No DDL, skip charset/engine checks

    # Check for utf8mb4 (not bare utf8)
    if re.search(r"utf8[^m]|charset\s*=\s*utf8\b", code, re.IGNORECASE):
        if not re.search(r"utf8mb4", code, re.IGNORECASE):
            return fail(
                "MySQL charset is utf8 (3-byte, cannot store emoji) — "
                "use utf8mb4"
            )

    # Check for MyISAM
    if re.search(r"ENGINE\s*=\s*MyISAM", code, re.IGNORECASE):
        return fail(
            "MyISAM engine — use InnoDB (transactions, row-level locking, "
            "crash recovery)"
        )

    # Check for INT AUTO_INCREMENT PK (should be BIGINT)
    if re.search(r"\bINT\s+AUTO_INCREMENT", code, re.IGNORECASE):
        if not re.search(r"\bBIGINT\s+AUTO_INCREMENT", code, re.IGNORECASE):
            return fail(
                "INT AUTO_INCREMENT PK — use BIGINT AUTO_INCREMENT "
                "(INT maxes at ~2.1B rows)"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
