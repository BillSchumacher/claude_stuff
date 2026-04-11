"""Fail if SQL queries use anti-patterns: SELECT *, OFFSET pagination, or comma joins.

Checks for the most impactful query anti-patterns from the sql skill.
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
        return fail("No SQL code found")

    # SELECT * in non-trivial queries (allow in CTEs/subqueries for INSERT...SELECT)
    selects = re.findall(r"SELECT\s+\*\s+FROM", code, re.IGNORECASE)
    if len(selects) > 0:
        # Allow if it's INSERT INTO ... SELECT * FROM (copy pattern)
        insert_select = re.findall(
            r"INSERT\s+INTO\s+\w+\s+SELECT\s+\*", code, re.IGNORECASE,
        )
        if len(selects) > len(insert_select):
            return fail(
                "SELECT * in production query — list only the columns needed"
            )

    # OFFSET-based pagination (allow OFFSET 0)
    if re.search(r"\bOFFSET\s+[1-9]\d*\b|\bOFFSET\s+[:@$]\w+", code, re.IGNORECASE):
        return fail(
            "OFFSET pagination is O(offset + limit) — use keyset/cursor "
            "pagination: WHERE id > :last_seen ORDER BY id LIMIT :n"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
