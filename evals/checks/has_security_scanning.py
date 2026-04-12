"""Check that CI/CD pipeline includes a dependency security audit step.

Looks for: npm audit, pip-audit, cargo audit, govulncheck, composer audit,
dotnet list package --vulnerable, safety check, snyk, dependabot, trivy.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

AUDIT_PATTERNS = [
    # JavaScript
    r"npm\s+audit\b",
    r"yarn\s+audit\b",
    r"pnpm\s+audit\b",
    # Python
    r"pip-audit\b",
    r"safety\s+check\b",
    r"pip\s+audit\b",
    # Rust
    r"cargo\s+audit\b",
    r"cargo\s+deny\b",
    # Go
    r"govulncheck\b",
    r"nancy\s+sleuth\b",
    # PHP
    r"composer\s+audit\b",
    # C#
    r"dotnet\s+list\s+package\s+--vulnerable",
    # C/C++
    r"cppcheck\b",
    r"clang-tidy\b",
    # Cross-language tools
    r"snyk\b",
    r"trivy\b",
    r"grype\b",
    r"osv-scanner\b",
    r"dependabot\b",
    r"renovate\b",
    r"gitleaks\b",
    r"trufflehog\b",
    r"semgrep\b",
    r"codeql\b",
    r"sonarqube\b",
    r"sonarcloud\b",
]


def main() -> int:
    stdin = sys.stdin.read()

    code = get_all_code(
        stdin,
        languages=("yaml", "yml", "bash", "sh", "shell", "dockerfile"),
        strip_docs=False,
    )
    code += "\n" + stdin

    if not code.strip():
        return fail("No CI/CD configuration found")

    for pattern in AUDIT_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return 0

    return fail(
        "No security scanning or dependency audit step found in CI pipeline. "
        "Expected: npm audit, pip-audit, cargo audit, govulncheck, composer audit, "
        "snyk, trivy, or similar."
    )


if __name__ == "__main__":
    sys.exit(main())
