"""Fail if weak cryptographic primitives are used (MD5, SHA-1, plain SHA-256 for passwords, DES)."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    weak_patterns = [
        (r"hashlib\.md5\b", "hashlib.md5"),
        (r"hashlib\.sha1\b", "hashlib.sha1"),
        (r"hashlib\.new\(\s*['\"](?:md5|sha1)['\"]", "hashlib.new('md5'/'sha1')"),
        (r"\bMD5\b", "MD5"),
        (r"\bDES\b", "DES"),
        (r"\b3DES\b", "3DES"),
        (r"\.encrypt_mode\s*=\s*[A-Za-z_.]*ECB", "ECB mode"),
        (r"AES\.MODE_ECB", "AES.MODE_ECB"),
    ]
    for pattern, label in weak_patterns:
        if re.search(pattern, code):
            return fail(f"Weak crypto: {label}")

    # Password hashing context: if 'password' appears near hashlib.sha256 / sha512
    # without bcrypt/argon2/scrypt nearby, that's also weak.
    password_hash_context = re.search(
        r"(?:password|passwd|pwd)[^\n]*\n?[^\n]*hashlib\.(sha256|sha512)",
        code,
        re.IGNORECASE,
    )
    if password_hash_context:
        # Allow if a proper password hash function is also present
        if not re.search(r"\b(bcrypt|argon2|scrypt|pbkdf2)", code, re.IGNORECASE):
            return fail(
                "Plain SHA-256/SHA-512 used for password hashing "
                "(use bcrypt, argon2id, or scrypt instead)"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
