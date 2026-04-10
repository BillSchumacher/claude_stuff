"""Fail if pickle, yaml.load (unsafe), or marshal are used on input data."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    bad_patterns = [
        (r"\bpickle\.loads?\s*\(", "pickle.load/loads"),
        (r"\bcPickle\.loads?\s*\(", "cPickle.load/loads"),
        (r"\bmarshal\.loads?\s*\(", "marshal.load/loads"),
        # yaml.load without explicit SafeLoader
        (r"yaml\.load\s*\((?![^)]*Loader\s*=\s*[^)]*Safe)", "yaml.load (use yaml.safe_load)"),
        (r"\bshelve\.open\s*\(", "shelve.open (uses pickle internally)"),
    ]
    for pattern, label in bad_patterns:
        if re.search(pattern, code):
            return fail(f"Unsafe deserialization: {label}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
