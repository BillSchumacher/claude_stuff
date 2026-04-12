"""Check that CREATE TABLE statements use NOT NULL on columns.

The sql skill requires: 'Declare NOT NULL on every column that should never
be null.' Tables with zero NOT NULL constraints are flagged.
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
    )
    if not code.strip():
        return 0  # No SQL code found

    # Find CREATE TABLE statements
    tables = re.findall(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s*\(([\s\S]*?)\)\s*;",
        code,
        re.IGNORECASE,
    )

    if not tables:
        return 0  # No DDL to check

    tables_without_not_null = []
    for name, body in tables:
        # Count column definitions (lines with a type name)
        col_lines = [
            line.strip() for line in body.split(",")
            if line.strip()
            and not re.match(r"(?:PRIMARY|FOREIGN|UNIQUE|CHECK|CONSTRAINT|INDEX)\b", line.strip(), re.IGNORECASE)
        ]
        if not col_lines:
            continue

        has_not_null = any(
            re.search(r"\bNOT\s+NULL\b", line, re.IGNORECASE)
            for line in col_lines
        )
        # PRIMARY KEY columns are implicitly NOT NULL, check for that too
        has_pk_inline = any(
            re.search(r"\bPRIMARY\s+KEY\b", line, re.IGNORECASE)
            for line in col_lines
        )

        if not has_not_null and not has_pk_inline:
            tables_without_not_null.append(name)

    if tables_without_not_null:
        return fail(
            f"Tables with no NOT NULL constraints: {', '.join(tables_without_not_null)} — "
            "declare NOT NULL on every column that should never be null"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
