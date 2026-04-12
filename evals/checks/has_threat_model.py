"""Check that the agent performed threat modeling before implementation.

Scans the agent's output messages for evidence of threat analysis:
threat model, attack surface, trust boundary, threat vector, risk assessment.
"""

import json
import os
import re
import sys


THREAT_MODEL_INDICATORS = [
    r"threat\s+model",
    r"attack\s+surface",
    r"trust\s+boundar",
    r"threat\s+vector",
    r"risk\s+assessment",
    r"security\s+consideration",
    r"attack\s+scenario",
    r"adversar",
    r"mitigation\s+strateg",
    r"security\s+risk",
    r"malicious\s+(?:user|input|file|request|actor)",
    r"path\s+traversal",
    r"injection\s+(?:attack|risk|vector|vulnerabilit)",
    r"file\s+(?:type|extension|content)\s+validation",
    r"(?:prevent|protect|guard)\s+against",
    r"denial.of.service",
    r"vulnerabilit(?:y|ies)",
]

# Structured threat model section markers (from secure-coding skill template)
STRUCTURED_MARKERS = [
    r"##\s*Threat\s+Model",
    r"\*\*Assets",
    r"\*\*Trust\s+boundar",
    r"\*\*Threats:?\*\*",
    r"\*\*Assumptions:?\*\*",
    # STRIDE analysis markers
    r"STRIDE",
    r"\*\*Data\s+flow:?\*\*",
    r"\*\*Residual\s+risk",
    r"\bSpoofing\b.*\bTampering\b|\bTampering\b.*\bSpoofing\b",
    r"\bInfo(?:rmation)?\s+Disclosure\b",
    r"\bElevation\s+of\s+Priv",
    r"\bDenial\s+of\s+Service\b",
]

# Require at least this many distinct indicators for a meaningful threat model
MIN_INDICATORS = 2
# Or this many structured markers (structured format is always sufficient)
MIN_STRUCTURED = 2


def main() -> int:
    stdin = sys.stdin.read()

    # Also check messages file for assistant text
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

    # Check for structured threat model section first
    structured_found = []
    for pattern in STRUCTURED_MARKERS:
        if re.search(pattern, text, re.IGNORECASE):
            structured_found.append(pattern)

    if len(structured_found) >= MIN_STRUCTURED:
        print(
            f"Structured threat model detected: {len(structured_found)} markers found",
            file=sys.stderr,
        )
        return 0

    # Fall back to indicator-based detection
    found = []
    for pattern in THREAT_MODEL_INDICATORS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(pattern)

    if len(found) < MIN_INDICATORS:
        print(
            f"Insufficient threat modeling evidence. "
            f"Found {len(found)}/{MIN_INDICATORS} required indicators, "
            f"{len(structured_found)}/{MIN_STRUCTURED} structured markers. "
            f"Expected: ## Threat Model section with Assets/Threats/Trust boundaries, "
            f"or discussion of attack surface, vulnerabilities, mitigations.",
            file=sys.stderr,
        )
        return 1

    print(f"Threat modeling detected: {len(found)} indicators found", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
