"""Check that all functions in the output have docstrings."""

import ast
import re
import sys


def main() -> int:
    output = sys.stdin.read()
    blocks = re.findall(r"```python\n(.*?)```", output, re.DOTALL)
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
