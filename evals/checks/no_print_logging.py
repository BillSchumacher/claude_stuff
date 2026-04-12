"""Fail if production service code uses print() instead of structured logging.

Applies to Python code in production service context (not scripts/CLIs).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read(), languages=("python", "py"))
    if not code.strip():
        return 0  # No Python code

    has_print = bool(re.search(r"\bprint\s*\(", code))
    has_logger = bool(re.search(
        r"\blogging\b|\bstructlog\b|\blogger\b|\bgetLogger\b|\blog\.\w+\(",
        code,
    ))

    if has_print and not has_logger:
        return fail(
            "Service uses print() for output but no structured logger. "
            "Use logging, structlog, or equivalent for production services."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
