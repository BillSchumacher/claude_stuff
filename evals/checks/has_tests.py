"""Check that the output includes test code (in text or written files)."""

import json
import os
import re
import sys


def get_written_content(messages: list[dict]) -> str:
    """Extract content from all Write tool calls in the message stream."""
    parts = []
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        for content in msg.get("message", {}).get("content", []):
            if content.get("type") == "tool_use" and content.get("name") == "Write":
                parts.append(content.get("input", {}).get("content", ""))
    return "\n".join(parts)


def main() -> int:
    output = sys.stdin.read()

    # Also check files written via tool calls if available
    msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
    if msgs_file:
        with open(msgs_file, encoding="utf-8") as f:
            messages = json.load(f)
        output += "\n" + get_written_content(messages)

    # Check code blocks in text output
    blocks = re.findall(r"```python\n(.*?)```", output, re.DOTALL)
    code = "\n".join(blocks) + "\n" + output

    test_patterns = [
        r"def test_",
        r"assert ",
        r"pytest",
        r"unittest",
    ]
    if not any(re.search(p, code) for p in test_patterns):
        print("No test code found in output or written files", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
