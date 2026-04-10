"""Fail if Python code does membership testing against data that should be a hash set.

Passes if a `set(`, `frozenset(`, or set comprehension `{... for ...}` is present
AND a membership test exists. Fails if membership is tested but the collection is
built as a list (list comprehension, repeated .append, or plain list literal).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    # Is there a membership test at all? (`x in <name>` where name is not range/dict call)
    has_membership = bool(
        re.search(r"\bin\s+\w+\b", code)
        and not re.search(r"\bin\s+range\s*\(", code)
    )
    if not has_membership:
        return 0

    # Positive signal: set( or frozenset( call, or set-comprehension braces.
    # A set-comprehension is `{expr for ... in ...}` — we distinguish from dict
    # comprehensions by absence of `:` before `for`.
    has_set_ctor = bool(re.search(r"\b(frozen)?set\s*\(", code))
    has_set_comp = bool(
        re.search(r"\{\s*[^:}\n]+\s+for\s+\w+\s+in\s+", code)
    )
    if has_set_ctor or has_set_comp:
        return 0

    # Strong negative signal: the collection was loaded with a list comprehension
    # `[x for x in ...]` or `list(...)` call, and membership is tested.
    has_list_load = bool(
        re.search(r"\[\s*\w+(?:\.\w+\(\))?\s+for\s+\w+\s+in\s+", code)
        or re.search(r"\blist\s*\(", code)
    )
    if has_list_load:
        return fail(
            "Collection built as a list and used for membership test "
            "(O(n) per lookup). Load into a set / frozenset for O(1) lookup."
        )

    # Fallback: membership test exists but no set created anywhere.
    return fail(
        "Membership tests present but no set/frozenset constructed. "
        "For repeated membership, build a set once (O(1) per lookup)."
    )


if __name__ == "__main__":
    sys.exit(main())
