"""Fail if insecure RNG is used for security-sensitive values (tokens, keys, passwords).

Multi-language: Python random, Go math/rand, JS Math.random, PHP rand/mt_rand,
C# System.Random.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

SECURITY_CONTEXT = re.compile(
    r"\b(token|secret|password|session|nonce|csrf|api[_-]?key|salt)\b",
    re.IGNORECASE,
)

INSECURE_PATTERNS = [
    # Python
    (r"\brandom\.(?:random|randint|choice|choices|sample|getrandbits|uniform)\b",
     "Python random module", r"import secrets|from secrets"),
    # Go math/rand
    (r"\brand\.(?:Intn|Int|Int63|Float64|Float32|Uint32|Uint64|Perm|Shuffle)\b",
     "Go math/rand", r"crypto/rand"),
    # JavaScript
    (r"\bMath\.random\s*\(", "Math.random()",
     r"crypto\.randomBytes|crypto\.getRandomValues|crypto\.randomUUID|randomUUID"),
    # PHP
    (r"\b(?:rand|mt_rand|array_rand)\s*\(", "PHP rand/mt_rand",
     r"random_bytes|random_int|openssl_random_pseudo_bytes"),
    # C#
    (r"\bnew\s+Random\s*\(|Random\.Next|Random\.Shared",
     "System.Random", r"RandomNumberGenerator|RNGCryptoServiceProvider"),
    # C/C++
    (r"\brand\s*\(\s*\)|srand\s*\(", "C rand()/srand()",
     r"getrandom|RAND_bytes|BCryptGenRandom|arc4random"),
]


def main() -> int:
    stdin = sys.stdin.read()
    code = get_all_code(
        stdin,
        languages=(
            "python", "py", "go", "golang", "javascript", "js",
            "typescript", "ts", "php", "csharp", "cs", "rust", "rs",
            "c", "cpp", "c++",
        ),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No code found")

    if not SECURITY_CONTEXT.search(code):
        return 0  # Not security-sensitive context

    for pattern, label, safe_pattern in INSECURE_PATTERNS:
        if re.search(pattern, code):
            if not re.search(safe_pattern, code):
                return fail(
                    f"Insecure RNG ({label}) used for security-sensitive value"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
