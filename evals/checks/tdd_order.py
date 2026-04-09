"""Check that the agent followed TDD: write tests -> run (fail) -> write impl -> run (pass)."""

import json
import os
import sys


def extract_events(messages: list[dict]) -> list[dict]:
    """Extract ordered tool_use and tool_result events from stream-json messages."""
    events = []
    tool_id_map: dict[str, str] = {}

    for msg in messages:
        msg_type = msg.get("type")
        if msg_type == "assistant":
            for content in msg.get("message", {}).get("content", []):
                if content.get("type") == "tool_use":
                    tool_id = content.get("id", "")
                    tool_id_map[tool_id] = content["name"]
                    events.append({
                        "kind": "tool_use",
                        "name": content["name"],
                        "input": content.get("input", {}),
                        "id": tool_id,
                    })
        elif msg_type == "user":
            # Tool results come as user messages with tool_result content
            for content in msg.get("message", {}).get("content", []):
                if isinstance(content, dict) and content.get("type") == "tool_result":
                    tool_id = content.get("tool_use_id", "")
                    events.append({
                        "kind": "tool_result",
                        "name": tool_id_map.get(tool_id, "unknown"),
                        "content": content.get("content", ""),
                        "is_error": content.get("is_error", False),
                        "id": tool_id,
                    })
    return events


def classify_write(event: dict) -> list[str]:
    """Classify a Write tool call. Returns list: 'test', 'impl', or both."""
    inp = event["input"]
    path = inp.get("file_path", "").lower()
    content = inp.get("content", "").lower()

    is_test_path = "test" in os.path.basename(path)
    has_test_funcs = "def test_" in content
    non_test_defs = any(
        line.strip().startswith(("def ", "class "))
        and not line.strip().startswith("def test_")
        for line in content.splitlines()
    )

    results = []
    if is_test_path or has_test_funcs:
        results.append("test")
    if non_test_defs and not is_test_path:
        results.append("impl")
    return results


def is_test_run(event: dict) -> bool:
    """Check if a Bash tool call runs a test suite."""
    cmd = event["input"].get("command", "").lower()
    return any(r in cmd for r in ["pytest", "python -m pytest", "unittest", "nose"])


def test_run_failed(event: dict, events: list[dict]) -> bool | None:
    """Check if a test run's result indicates failure. Returns None if result not found."""
    tool_id = event["id"]
    for e in events:
        if e["kind"] == "tool_result" and e["id"] == tool_id:
            content = str(e.get("content", "")).lower()
            if e.get("is_error"):
                return True
            if "failed" in content or "error" in content or "importerror" in content:
                return True
            if "passed" in content:
                return False
            # Non-zero exit codes show up in error content
            return True  # Assume failure if unclear
    return None


def check_tdd_order(events: list[dict]) -> tuple[bool, str]:
    """Verify the full TDD cycle: write test -> run test (fail) -> write impl -> run test (pass)."""
    # Build simplified timeline
    timeline = []
    for e in events:
        if e["kind"] != "tool_use":
            continue
        if e["name"] == "Write":
            for kind in classify_write(e):
                timeline.append(("write_" + kind, e))
        elif e["name"] == "Bash" and is_test_run(e):
            failed = test_run_failed(e, events)
            label = "run_test_fail" if failed else "run_test_pass"
            timeline.append((label, e))

    labels = [t[0] for t in timeline]

    if not labels:
        return False, "No Write or test-run tool calls found in messages"

    # Check step 1: test file written
    first_test = next((i for i, l in enumerate(labels) if l == "write_test"), None)
    if first_test is None:
        return False, f"No test file was written. Events: {labels}"

    # Check step 2: test run (should fail) after writing tests, before writing impl
    first_impl = next((i for i, l in enumerate(labels) if l == "write_impl"), None)

    # Find test runs after first test write
    test_runs_after_test = [
        (i, labels[i]) for i in range(first_test + 1, len(labels))
        if labels[i].startswith("run_test")
    ]

    if not test_runs_after_test:
        return False, (
            f"Tests were written but never executed. Events: {labels}"
        )

    if first_impl is None:
        return False, f"No implementation file was written. Events: {labels}"

    if first_test > first_impl:
        return False, (
            f"Implementation written before tests. "
            f"First impl at {first_impl}, first test at {first_test}. Events: {labels}"
        )

    # Check: test run between writing tests and writing impl
    runs_before_impl = [
        (i, l) for i, l in test_runs_after_test if i < first_impl
    ]
    if not runs_before_impl:
        return False, (
            f"Tests written before implementation, but not executed before implementing. "
            f"Events: {labels}"
        )

    # Check: the pre-impl test run should have failed
    first_run_idx, first_run_label = runs_before_impl[0]
    if first_run_label != "run_test_fail":
        return False, (
            f"Tests were run before implementation but did not fail "
            f"(expected failing tests to prove they work). Events: {labels}"
        )

    # Check step 4: test run after impl (should pass)
    runs_after_impl = [
        (i, l) for i, l in test_runs_after_test if i > first_impl
    ]
    if not runs_after_impl:
        return False, (
            f"Implementation written but tests were not re-run afterward. Events: {labels}"
        )

    return True, (
        f"TDD cycle verified: write_test@{first_test}, "
        f"run_test_fail@{first_run_idx}, write_impl@{first_impl}, "
        f"run_test@{runs_after_impl[0][0]}. Events: {labels}"
    )


def main() -> int:
    msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
    if not msgs_file:
        print("EVAL_MESSAGES_FILE not set — cannot check TDD order", file=sys.stderr)
        return 1

    with open(msgs_file, encoding="utf-8") as f:
        messages = json.load(f)

    events = extract_events(messages)
    passed, detail = check_tdd_order(events)
    if not passed:
        print(detail, file=sys.stderr)
    else:
        print(detail, file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
