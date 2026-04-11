"""Fail if API keys, tokens, or passwords are hardcoded in the source."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(
        sys.stdin.read(),
        languages=(
            "python", "py", "go", "golang", "javascript", "js",
            "typescript", "ts", "php", "csharp", "cs", "rust", "rs",
            "c", "cpp", "c++",
        ),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code:
        return fail("No code found")

    # Look for assignments like API_KEY = "abc123def..." or password = "..."
    # Handles Python =, Go :=, and other assignment styles
    secret_var_pattern = re.compile(
        r'\b(api_key|apikey|secret|token|password|passwd|access_key|private_key|auth_token)\s*:?=\s*["\']([^"\']{8,})["\']',
        re.IGNORECASE,
    )
    placeholder_values = {
        "your_api_key_here", "your-api-key-here", "changeme", "xxx", "todo",
        "your_token_here", "your_secret_here", "placeholder", "example",
        "your_password", "<your_api_key>", "your_key_here",
    }
    # Allow obvious env var loading patterns
    env_load_indicators = ("os.environ", "os.getenv", "getenv(", "environ[", "getpass.")

    for match in secret_var_pattern.finditer(code):
        var_name = match.group(1)
        value = match.group(2)
        # Skip obvious placeholders
        if value.lower() in placeholder_values or value.lower().startswith("<"):
            continue
        # Allow if the line contains env var loading
        line_start = code.rfind("\n", 0, match.start()) + 1
        line_end = code.find("\n", match.end())
        line = code[line_start:line_end if line_end != -1 else len(code)]
        if any(ind in line for ind in env_load_indicators):
            continue
        return fail(
            f"Hardcoded secret-like value: {var_name} = {value[:30]}..."
        )

    # Look for high-entropy strings that look like real keys
    high_entropy = re.compile(
        r'["\']([A-Za-z0-9_\-]{32,})["\']'
    )
    # Only flag if assigned to a secret-named variable nearby
    for match in high_entropy.finditer(code):
        value = match.group(1)
        # Check 60 chars before for a secret-named variable
        ctx = code[max(0, match.start() - 80):match.start()].lower()
        if any(name in ctx for name in ["api_key", "secret", "token", "password"]):
            if "os.environ" not in ctx and "getenv" not in ctx:
                return fail(f"Hardcoded high-entropy secret: {value[:20]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
