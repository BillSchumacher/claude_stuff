"""Check that the agent produced a structured complexity analysis.

Looks for the complexity analysis format from the efficient-code skill:
- ## Complexity Analysis heading
- Big-O notation in a table or structured discussion
- Comparison of approaches (naive vs recommended)
"""

import json
import os
import re
import sys


# Structured markers from the efficient-code skill template
STRUCTURED_MARKERS = [
    r"##\s*Complexity\s+Analysis",
    r"\bO\([n²nmk\s\d*log]+\)",       # Big-O notation like O(n), O(n²), O(n log n)
    r"\|\s*O\(",                        # Big-O inside a table cell
    r"\*\*(?:Problem|Input size|Selected|Priority):?\*\*",
    r"(?:Naive|Brute.force|Recommended|Current|Suggested|Approach)",
]

# Fallback: any structured Big-O discussion
BIGO_INDICATORS = [
    r"O\(n[²2]\)",                       # quadratic
    r"O\(n\s*(?:log|·)\s*[nmk]\)",       # n log n or n·m
    r"O\(n\s*\+\s*m\)",                  # linear two-collection
    r"O\(1\)",                           # constant
    r"O\(n\)",                           # linear
    r"O\(log\s*n\)",                     # logarithmic
    r"time\s+complexity",
    r"space\s+complexity",
    r"(?:quadratic|linear|logarithmic|constant)\s+(?:time|space|complexity)",
]

MIN_STRUCTURED = 2
MIN_BIGO = 2


def main() -> int:
    stdin = sys.stdin.read()

    text = stdin
    msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
    if msgs_file:
        with open(msgs_file, encoding="utf-8") as f:
            messages = json.load(f)
        for msg in messages:
            if msg.get("type") == "assistant":
                for content in msg.get("message", {}).get("content", []):
                    if content.get("type") == "text":
                        text += "\n" + content.get("text", "")

    if not text.strip():
        print("No output text found", file=sys.stderr)
        return 1

    # Check for structured complexity analysis first
    structured_found = sum(
        1 for p in STRUCTURED_MARKERS
        if re.search(p, text, re.IGNORECASE)
    )

    if structured_found >= MIN_STRUCTURED:
        print(
            f"Structured complexity analysis detected: "
            f"{structured_found} markers found",
            file=sys.stderr,
        )
        return 0

    # Fall back to Big-O indicator detection
    bigo_found = sum(
        1 for p in BIGO_INDICATORS
        if re.search(p, text, re.IGNORECASE)
    )

    if bigo_found >= MIN_BIGO:
        print(
            f"Complexity discussion detected: {bigo_found} Big-O indicators found",
            file=sys.stderr,
        )
        return 0

    print(
        f"No complexity analysis found. "
        f"Found {structured_found}/{MIN_STRUCTURED} structured markers, "
        f"{bigo_found}/{MIN_BIGO} Big-O indicators. "
        f"Expected: ## Complexity Analysis section with Big-O comparison table, "
        f"or discussion of time/space complexity with O() notation.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
