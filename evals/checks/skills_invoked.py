"""Check that specific skills were invoked by the agent during the run.

Reads EVAL_MESSAGES_FILE to inspect the message stream for Skill tool calls.
Reads EVAL_EXPECTED_SKILLS (comma-separated) to know which skills should appear.
"""

import json
import os
import sys


def extract_invoked_skills(messages: list[dict]) -> list[str]:
    """Extract names of skills invoked via the Skill tool in the message stream."""
    invoked = []
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        for content in msg.get("message", {}).get("content", []):
            if content.get("type") == "tool_use" and content.get("name") == "Skill":
                skill_name = content.get("input", {}).get("skill", "")
                if skill_name:
                    invoked.append(skill_name)
    return invoked


def main() -> int:
    msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
    expected_raw = os.environ.get("EVAL_EXPECTED_SKILLS", "")

    if not msgs_file:
        print("EVAL_MESSAGES_FILE not set", file=sys.stderr)
        return 1
    if not expected_raw:
        print("EVAL_EXPECTED_SKILLS not set", file=sys.stderr)
        return 1

    expected = [s.strip() for s in expected_raw.split(",") if s.strip()]

    with open(msgs_file, encoding="utf-8") as f:
        messages = json.load(f)

    invoked = extract_invoked_skills(messages)
    # Skill names may be namespaced like "plugin-name:skill-name" or "skill-name"
    # Normalize by taking the part after ":" if present
    normalized = {s.split(":")[-1] for s in invoked}

    missing = [s for s in expected if s not in normalized]
    if missing:
        print(
            f"Expected skills not invoked: {missing}. "
            f"Skills invoked: {invoked or 'none'}",
            file=sys.stderr,
        )
        return 1

    print(f"Skills invoked: {invoked}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
