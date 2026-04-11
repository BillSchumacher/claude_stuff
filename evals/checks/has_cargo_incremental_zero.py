"""Fail if Rust CI does not set CARGO_INCREMENTAL=0.

Incremental compilation wastes time and disk in CI (no prior state to
build on). CARGO_INCREMENTAL=0 produces faster clean builds.
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

    if re.search(r"CARGO_INCREMENTAL.*0|CARGO_INCREMENTAL:\s*['\"]?0", code):
        return 0

    return fail(
        "Rust CI missing CARGO_INCREMENTAL=0 — set it to disable "
        "incremental compilation for faster, more reproducible CI builds"
    )


if __name__ == "__main__":
    sys.exit(main())
