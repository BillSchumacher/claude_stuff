"""Fail if logging statements include passwords, tokens, secrets, or full auth headers."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    # Find log statements that mention sensitive variable names
    log_call = re.compile(
        r"(?:logger?|log|logging)\.(?:debug|info|warning|error|critical|exception)\s*\(([^)]+)\)",
        re.IGNORECASE,
    )
    sensitive = re.compile(
        r"\b(password|passwd|pwd|secret|token|api[_-]?key|authorization|auth_header|session_id|jwt|bearer)\b",
        re.IGNORECASE,
    )

    for match in log_call.finditer(code):
        args = match.group(1)
        if sensitive.search(args):
            # Allow if it looks redacted ("***", "[REDACTED]", masked, etc.)
            if any(t in args.lower() for t in ["redact", "mask", "***", "[hidden]", "obscur"]):
                continue
            return fail(f"Logging sensitive value: {match.group(0)[:120]}")

    # Also flag print() of full request bodies / headers
    print_headers = re.search(
        r'print\([^)]*\b(headers|request\.headers|cookies|authorization)\b',
        code,
        re.IGNORECASE,
    )
    if print_headers:
        return fail(f"Printing headers/cookies (may contain auth): {print_headers.group(0)[:120]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
