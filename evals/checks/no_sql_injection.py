"""Fail if SQL queries use string formatting/concatenation instead of parameters."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    sql_keywords = r"(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION)"
    bad_patterns = [
        # f-string SQL: f"SELECT ... {var}"
        (rf'f["\'](?:[^"\']*?){sql_keywords}[^"\']*?\{{[^}}]+\}}', "f-string SQL"),
        # %-formatted SQL: "SELECT ... %s" % var
        (rf'["\'](?:[^"\']*?){sql_keywords}[^"\']*?["\'](?:\s*%\s*)', "%-formatted SQL"),
        # Concatenated SQL: "SELECT ... " + var
        (rf'["\'](?:[^"\']*?){sql_keywords}[^"\']*?["\']\s*\+', "concatenated SQL"),
        # .format() SQL: "SELECT ... {}".format(var)
        (rf'["\'](?:[^"\']*?){sql_keywords}[^"\']*?\{{\}}[^"\']*?["\']\s*\.format\(', ".format() SQL"),
    ]

    for pattern, label in bad_patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return fail(f"Detected {label}: {match.group(0)[:100]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
