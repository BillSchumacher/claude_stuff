"""Check that threat modeling occurs before code changes in the message stream.

Reads EVAL_MESSAGES_FILE to find the first assistant message containing
threat model markers and the first Edit/Write tool call. The threat model
must appear in an earlier message (or the same message before the tool call).
"""

import json
import os
import re
import sys

THREAT_MARKERS = [
    r"##\s*Threat\s+Model",
    r"\*\*Assets",
    r"\*\*Threats:?\*\*",
    r"\*\*Trust\s+boundar",
    # STRIDE markers
    r"STRIDE",
    r"\*\*Data\s+flow:?\*\*",
    r"\bSpoofing\b",
    r"\bElevation\s+of\s+Priv",
]

CODE_TOOLS = {"Edit", "Write"}

MIN_MARKERS = 2


def main() -> int:
    msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
    if not msgs_file:
        print("EVAL_MESSAGES_FILE not set", file=sys.stderr)
        return 1

    with open(msgs_file, encoding="utf-8") as f:
        messages = json.load(f)

    threat_model_index = None
    first_code_index = None

    for i, msg in enumerate(messages):
        if msg.get("type") != "assistant":
            continue

        contents = msg.get("message", {}).get("content", [])

        # Check for threat model in text blocks
        if threat_model_index is None:
            for content in contents:
                if content.get("type") == "text":
                    text = content.get("text", "")
                    found = sum(
                        1 for p in THREAT_MARKERS
                        if re.search(p, text, re.IGNORECASE)
                    )
                    if found >= MIN_MARKERS:
                        threat_model_index = i
                        break

        # Check for code-changing tool calls
        if first_code_index is None:
            for content in contents:
                if (content.get("type") == "tool_use"
                        and content.get("name") in CODE_TOOLS):
                    first_code_index = i
                    break

    if threat_model_index is None:
        print(
            "No structured threat model found in message stream",
            file=sys.stderr,
        )
        return 1

    if first_code_index is None:
        # No code changes made — threat model still counts
        print(
            "Threat model found (no code changes in stream)",
            file=sys.stderr,
        )
        return 0

    if threat_model_index <= first_code_index:
        print(
            f"Threat model (message {threat_model_index}) appears before "
            f"first code change (message {first_code_index})",
            file=sys.stderr,
        )
        return 0

    print(
        f"Threat model (message {threat_model_index}) appears AFTER "
        f"first code change (message {first_code_index}) — "
        "threat model should come first",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
