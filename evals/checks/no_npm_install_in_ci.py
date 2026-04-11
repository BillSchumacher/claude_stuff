"""Fail if CI uses `npm install` instead of `npm ci`.

`npm ci` deletes node_modules and installs from lockfile — it's faster,
deterministic, and the correct choice for CI. `npm install` may mutate
the lockfile.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=("yaml", "yml"),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No YAML workflow found")

    # Check for npm install (but not npm ci, npm ci is fine)
    if re.search(r"\bnpm install\b", code):
        # Make sure it's not just in a comment
        if not re.search(r"\bnpm ci\b", code):
            return fail(
                "Uses `npm install` instead of `npm ci` — "
                "npm ci is faster and installs from lockfile deterministically"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
