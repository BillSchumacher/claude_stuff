"""Check that all functions in the output have docstrings."""

import ast
import json
import os
import re
import sys


def _get_written_python_blocks(msgs_file: str) -> list[str]:
    """Extract content from Write tool calls targeting .py files."""
    with open(msgs_file, encoding="utf-8") as f:
        messages = json.load(f)
    blocks = []
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        for cb in msg.get("message", {}).get("content", []):
            if cb.get("type") != "tool_use" or cb.get("name") != "Write":
                continue
            fp = cb.get("input", {}).get("file_path", "")
            if fp.endswith(".py") and not os.path.basename(fp).startswith("test"):
                blocks.append(cb["input"]["content"])
    return blocks


def main() -> int:
    output = sys.stdin.read()
    blocks = re.findall(r"```python\n(.*?)```", output, re.DOTALL)

    # Fall back to written Python files when no code blocks in output
    if not blocks:
        msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
        if msgs_file:
            blocks = _get_written_python_blocks(msgs_file)

    if not blocks:
        print("No Python code blocks found", file=sys.stderr)
        return 1

    for block in blocks:
        try:
            tree = ast.parse(block)
        except SyntaxError as e:
            print(f"Syntax error: {e}", file=sys.stderr)
            return 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    print(
                        f"Function '{node.name}' lacks docstring",
                        file=sys.stderr,
                    )
                    return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
