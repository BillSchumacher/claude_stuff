"""Fail if weak cryptographic primitives are used (MD5, SHA-1, DES, ECB, plain SHA for passwords).

Multi-language: Python hashlib, Go crypto/md5, JS crypto.createHash,
PHP md5/sha1, C# MD5.Create.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

WEAK_PATTERNS = [
    # Python
    (r"hashlib\.md5\b", "hashlib.md5"),
    (r"hashlib\.sha1\b", "hashlib.sha1"),
    (r"hashlib\.new\(\s*['\"](?:md5|sha1)['\"]", "hashlib.new('md5'/'sha1')"),
    (r"AES\.MODE_ECB", "AES.MODE_ECB"),
    # Go
    (r"\bmd5\.(?:New|Sum)\b", "Go crypto/md5"),
    (r"\bsha1\.(?:New|Sum)\b", "Go crypto/sha1"),
    (r"\bdes\.\w+", "Go crypto/des"),
    # JavaScript / TypeScript
    (r"createHash\s*\(\s*['\"]md5['\"]", "JS crypto.createHash('md5')"),
    (r"createHash\s*\(\s*['\"]sha1['\"]", "JS crypto.createHash('sha1')"),
    # PHP
    (r"\bmd5\s*\(\s*\$", "PHP md5()"),
    (r"\bsha1\s*\(\s*\$", "PHP sha1()"),
    # C#
    (r"MD5\.Create\s*\(", "C# MD5.Create()"),
    (r"SHA1\.Create\s*\(", "C# SHA1.Create()"),
    (r"MD5CryptoServiceProvider", "C# MD5CryptoServiceProvider"),
    # Universal
    (r"\bDES\b", "DES"),
    (r"\b3DES\b", "3DES"),
    (r"encrypt_mode\s*=\s*[A-Za-z_.]*ECB|ECB_MODE", "ECB mode"),
]

PASSWORD_HASH_PATTERNS = [
    # Python: sha256 near password
    r"(?:password|passwd|pwd)[^\n]*\n?[^\n]*hashlib\.(?:sha256|sha512)",
    # Go: sha256 near password
    r"(?:password|passwd|pwd)[^\n]*\n?[^\n]*sha256\.(?:New|Sum)",
    # JS: createHash('sha256') near password
    r"(?:password|passwd|pwd)[^\n]*\n?[^\n]*createHash\s*\(\s*['\"]sha256['\"]",
    # PHP: hash('sha256', $password)
    r"hash\s*\(\s*['\"]sha256['\"][^)]*(?:password|passwd|pwd)",
    # C#: SHA256.Create() near password
    r"(?:password|passwd|pwd)[^\n]*\n?[^\n]*SHA256\.Create",
]

SAFE_PASSWORD_HASH = r"\b(?:bcrypt|argon2|scrypt|pbkdf2|password_hash|Rfc2898DeriveBytes|PBKDF2)\b"


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

    for pattern, label in WEAK_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return fail(f"Weak crypto: {label}")

    for pattern in PASSWORD_HASH_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            if not re.search(SAFE_PASSWORD_HASH, code, re.IGNORECASE):
                return fail(
                    "Plain SHA-256/SHA-512 used for password hashing — "
                    "use bcrypt, argon2id, or scrypt instead"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
