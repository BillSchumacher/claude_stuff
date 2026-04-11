"""Fail if code exposes stack traces or raw exception messages to users.

Detects: traceback in response, str(e)/repr(e) in jsonify/return,
debug=True in production config.
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

    # traceback in a return/response
    if re.search(r"(?:return|jsonify|json\.dumps).*traceback\.", code):
        return fail(
            "Stack trace returned to client — log server-side, "
            "return a generic error message to the user"
        )

    # traceback.format_exc() stored and returned
    if re.search(r"traceback\.format_exc\(\)", code):
        # Check if it flows into a response (vs just logging)
        if not re.search(r"log(?:ger)?\.(?:error|exception|warning)", code):
            return fail(
                "traceback.format_exc() used without logging — "
                "if this reaches the client, it leaks internals"
            )

    # str(e) / repr(e) in jsonify or return
    if re.search(
        r"(?:jsonify|return\s+\{).*(?:str|repr)\s*\(\s*e\s*\)", code,
    ):
        return fail(
            "Raw exception message (str(e)) returned to client — "
            "return a generic error, log the details server-side"
        )

    # debug=True in app config
    if re.search(r"debug\s*=\s*True|DEBUG\s*=\s*True", code):
        return fail(
            "debug=True exposes stack traces to users — "
            "disable debug mode in production"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
