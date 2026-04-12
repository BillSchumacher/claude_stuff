"""Check that CI/CD pipeline uses frozen/locked dependency installation.

Reproducible builds require: npm ci, yarn install --immutable,
pnpm install --frozen-lockfile, pip install -r ... --no-deps,
pipenv install --deploy, poetry install --no-interaction,
uv sync --frozen, composer install --no-interaction, dotnet restore --locked-mode,
cargo fetch --locked.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, get_all_code_c_style, fail

FROZEN_INSTALL_PATTERNS = [
    # JavaScript
    r"npm\s+ci\b",
    r"yarn\s+install\s+--immutable",
    r"pnpm\s+install\s+--frozen-lockfile",
    # Python
    r"pipenv\s+install\s+--deploy",
    r"pip\s+install\s+.*--no-deps",
    r"poetry\s+install\b",
    r"uv\s+sync\s+--frozen",
    # PHP
    r"composer\s+install\s+--no-dev",
    r"composer\s+install\b",
    # C#
    r"dotnet\s+restore\s+--locked-mode",
    # Rust
    r"cargo\s+fetch\s+--locked",
    r"cargo\s+build\b",
    # Go
    r"go\s+mod\s+download",
]

# Anti-patterns: non-frozen install in CI
UNFROZEN_PATTERNS = [
    (r"npm\s+install\b(?!\s+--)", "npm install (use npm ci instead)"),
]


def main() -> int:
    stdin = sys.stdin.read()

    # Check both YAML and general code blocks
    code = get_all_code(
        stdin,
        languages=("yaml", "yml", "bash", "sh", "shell", "dockerfile"),
        strip_docs=False,
    )
    # Also check C-style code blocks for CI configs
    code += "\n" + get_all_code_c_style(
        stdin,
        languages=("yaml", "yml"),
    )
    # Include raw text for inline commands
    code += "\n" + stdin

    if not code.strip():
        return fail("No CI/CD configuration found")

    # Check for anti-patterns first
    for pattern, label in UNFROZEN_PATTERNS:
        if re.search(pattern, code):
            # Check if npm ci is also present (might be in a different step)
            if not re.search(r"npm\s+ci\b", code):
                return fail(f"Non-frozen install: {label}")

    # Check for at least one frozen install pattern
    for pattern in FROZEN_INSTALL_PATTERNS:
        if re.search(pattern, code):
            return 0

    return fail(
        "No frozen/locked dependency install found. "
        "Use npm ci, yarn --immutable, pipenv --deploy, etc. for reproducible CI builds."
    )


if __name__ == "__main__":
    sys.exit(main())
