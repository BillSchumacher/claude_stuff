"""Fail if subprocess uses shell=True with f-string/concatenation, or os.system with input."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    # subprocess.* with shell=True
    shell_true = re.search(r"subprocess\.\w+\([^)]*shell\s*=\s*True", code, re.DOTALL)
    if shell_true:
        # Check if the shell command has interpolation
        snippet = shell_true.group(0)
        if re.search(r'f["\']', snippet) or "+" in snippet or ".format" in snippet or "%" in snippet:
            return fail(f"subprocess with shell=True and string interpolation: {snippet[:120]}")
        # Even shell=True with constant string is risky if input is interpolated later
        return fail(f"subprocess with shell=True (avoid; pass list args): {snippet[:120]}")

    # os.system with anything other than constant string
    os_system = re.search(r"os\.system\(([^)]+)\)", code)
    if os_system:
        arg = os_system.group(1)
        if any(c in arg for c in ["+", "f'", 'f"', ".format", "%"]):
            return fail(f"os.system with interpolation: {os_system.group(0)[:120]}")

    # os.popen
    if re.search(r"\bos\.popen\(", code):
        return fail("os.popen is unsafe; use subprocess with list args")

    return 0


if __name__ == "__main__":
    sys.exit(main())
