"""Check that code uses streaming patterns instead of loading all data into memory."""

import re
import sys


def main() -> int:
    output = sys.stdin.read()
    blocks = re.findall(r"```python\n(.*?)```", output, re.DOTALL)
    if not blocks:
        print("No Python code blocks found", file=sys.stderr)
        return 1

    code = "\n".join(blocks)

    # Fail if entire file is read into a list/memory before processing
    bulk_patterns = [
        (r"\.readlines\(\)", "uses readlines() which loads entire file into memory"),
        (r"\.read\(\)", "uses read() which loads entire file into memory"),
        (r"json\.dumps?\(.*csv\.reader", "appears to load all CSV rows before writing JSON"),
    ]
    for pattern, reason in bulk_patterns:
        if re.search(pattern, code, re.DOTALL):
            print(reason, file=sys.stderr)
            return 1

    # Check for streaming indicators
    streaming_patterns = [
        r"for\s+\w+\s+in\s+",         # iterating with for loop
        r"csv\.(?:reader|DictReader)",  # using csv reader (lazy)
    ]
    has_streaming = any(re.search(p, code) for p in streaming_patterns)
    if not has_streaming:
        print("No streaming/iterative patterns found", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
