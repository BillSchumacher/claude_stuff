"""Fail if unsafe deserialization is used on input data.

Multi-language: Python pickle/marshal/yaml.load, PHP unserialize,
C# BinaryFormatter/SoapFormatter.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

BAD_PATTERNS = [
    # Python
    (r"\bpickle\.loads?\s*\(", "pickle.load/loads"),
    (r"\bcPickle\.loads?\s*\(", "cPickle.load/loads"),
    (r"\bmarshal\.loads?\s*\(", "marshal.load/loads"),
    (r"yaml\.load\s*\((?![^)]*Loader\s*=\s*[^)]*Safe)", "yaml.load (use yaml.safe_load)"),
    (r"\bshelve\.open\s*\(", "shelve.open (uses pickle internally)"),
    # PHP
    (r"\bunserialize\s*\(", "PHP unserialize() — use json_decode() instead"),
    # C#
    (r"BinaryFormatter\s*\(", "C# BinaryFormatter — use JsonSerializer instead"),
    (r"SoapFormatter\s*\(", "C# SoapFormatter"),
    (r"ObjectStateFormatter", "C# ObjectStateFormatter"),
    (r"NetDataContractSerializer", "C# NetDataContractSerializer"),
    (r"LosFormatter", "C# LosFormatter"),
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

    for pattern, label in BAD_PATTERNS:
        if re.search(pattern, code):
            return fail(f"Unsafe deserialization: {label}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
