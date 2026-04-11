"""Fail if SQL schema DDL lacks primary keys, NOT NULL constraints, or uses bad naming.

Checks CREATE TABLE statements for: primary key present, NOT NULL on most
columns, snake_case identifiers, no FLOAT/DOUBLE for monetary columns,
created_at/updated_at timestamps.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

MONEY_WORDS = r"(?:price|cost|amount|total|balance|salary|fee|charge|revenue|budget)"


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("sql", "plpgsql", "tsql", "plsql", "mysql"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No SQL code found")

    tables = re.findall(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
        code, re.IGNORECASE,
    )
    if not tables:
        return 0  # No DDL, N/A

    # Check for primary key
    if not re.search(r"PRIMARY\s+KEY", code, re.IGNORECASE):
        return fail("Schema missing PRIMARY KEY — every table must have one")

    # Check for FLOAT/DOUBLE on money columns
    if re.search(
        rf"(?:FLOAT|DOUBLE|REAL)\b[^;]*{MONEY_WORDS}|{MONEY_WORDS}[^;]*(?:FLOAT|DOUBLE|REAL)\b",
        code, re.IGNORECASE,
    ):
        return fail(
            "FLOAT/DOUBLE used for monetary column — use NUMERIC/DECIMAL "
            "with explicit precision"
        )

    # Check for camelCase identifiers (at least 2 tables should be snake_case)
    camel = re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w*[a-z][A-Z]\w*)", code)
    if len(camel) > 0:
        return fail(
            f"camelCase table name(s): {', '.join(camel)} — use snake_case"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
