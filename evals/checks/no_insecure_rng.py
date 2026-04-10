"""Fail if random.random/randint/choice is used for security-sensitive values (tokens, keys, passwords)."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    # If the code mentions tokens/keys/passwords/sessions and uses random.<x>
    # without using `secrets` module, that's insecure.
    security_context = re.search(
        r"\b(token|secret|password|session|nonce|csrf|api[_-]?key|salt)\b",
        code,
        re.IGNORECASE,
    )
    if not security_context:
        return 0  # Not security-sensitive, doesn't apply

    insecure_random = re.search(
        r"\brandom\.(?:random|randint|choice|choices|sample|getrandbits|uniform)\b",
        code,
    )
    if insecure_random:
        if "import secrets" not in code and "from secrets" not in code:
            return fail(
                f"Insecure RNG ({insecure_random.group(0)}) used for security-sensitive value. "
                "Use `secrets` module instead."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
