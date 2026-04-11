"""Fail if CI caches .tox/ directory instead of pip's download cache.

.tox/ contains full virtualenvs — caching it is fragile and bloated.
Cache ~/.cache/pip instead and let tox rebuild envs from cached wheels.
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

    if re.search(r"\.tox\b", code) and re.search(r"cache", code, re.IGNORECASE):
        # Check if .tox is in a cache path
        if re.search(r"path.*\.tox|\.tox.*path", code, re.DOTALL):
            return fail(
                "Caching .tox/ directory — cache ~/.cache/pip instead; "
                "tox envs rebuild cleanly from cached wheels"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
