"""Fail if code reads an entire file into memory when line-by-line iteration would work.

Detects: .readlines(), .read().split, f.read() followed by splitlines().
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    if re.search(r"\.readlines\s*\(\)", code):
        return fail(".readlines() loads entire file into memory; iterate with `for line in f:` instead")

    if re.search(r"\.read\s*\(\)\s*\.\s*split", code):
        return fail(".read().split() loads entire file; iterate with `for line in f:` instead")

    return 0


if __name__ == "__main__":
    sys.exit(main())
