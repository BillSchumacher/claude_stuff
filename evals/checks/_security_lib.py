"""Shared helpers for security check scripts.

Each check script extracts Python code from both:
- The agent's text output (markdown code blocks on stdin)
- Files written via the Write tool (from EVAL_MESSAGES_FILE)
"""

import json
import os
import re
import sys


def get_written_content(messages: list[dict]) -> str:
    """Concatenate content from all Write tool calls in the message stream."""
    parts = []
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        for content in msg.get("message", {}).get("content", []):
            if content.get("type") == "tool_use" and content.get("name") == "Write":
                parts.append(content.get("input", {}).get("content", ""))
    return "\n".join(parts)


def strip_docstrings_and_comments(code: str) -> str:
    """Remove triple-quoted strings, regular string literals, and # comments.

    Preserves f-strings (f"..." / f'...'), b-strings, and r-strings so that
    checks that intentionally match inside formatted strings (e.g., SQL
    injection via f-string) still work. Strips everything else that could
    accidentally contain a forbidden pattern in prose.
    """
    # Triple-quoted strings (docstrings or multi-line strings)
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    code = re.sub(r"'''[\s\S]*?'''", "", code)
    # Regular single/double quoted strings that are NOT f/b/r prefixed
    # (?<![a-zA-Z_]) ensures we don't strip f"...", b"...", r"...", rb"...", etc.
    code = re.sub(r'(?<![a-zA-Z_])"(?:[^"\\\n]|\\.)*"', '""', code)
    code = re.sub(r"(?<![a-zA-Z_])'(?:[^'\\\n]|\\.)*'", "''", code)
    # # comments
    code = re.sub(r"#[^\n]*", "", code)
    return code


def strip_c_style_comments(code: str) -> str:
    """Remove // line comments, /* */ block comments, and string literals.

    For C/C++/C#/JS/TS/Go/Rust/PHP code. Leaves template literals / raw strings
    alone since their syntax varies by language; that's rarely a source of
    false positives in efficiency checks.
    """
    # /* ... */ block comments (non-greedy)
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    # // line comments
    code = re.sub(r"//[^\n]*", "", code)
    # "..." and '...' string literals (single line only, allow backslash escapes)
    code = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', code)
    code = re.sub(r"'(?:[^'\\\n]|\\.)*'", "''", code)
    return code


def get_all_code(
    stdin_text: str,
    *,
    languages: tuple[str, ...] = ("python", "py"),
    strip_docs: bool = True,
) -> str:
    """Combine code from stdin code blocks and any written files.

    `languages` controls which fenced-code-block language tags are extracted.
    `strip_docs=True` runs the Python-style stripper (docstrings + # comments +
    regular string literals). For non-Python code use `get_all_code_c_style()`.
    """
    fence_langs = "|".join(re.escape(lang) for lang in languages)
    pattern = rf"```(?:{fence_langs})?\n(.*?)```"
    blocks = re.findall(pattern, stdin_text, re.DOTALL)
    code = "\n".join(blocks)

    msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
    if msgs_file:
        with open(msgs_file, encoding="utf-8") as f:
            messages = json.load(f)
        code += "\n" + get_written_content(messages)

    if strip_docs:
        code = strip_docstrings_and_comments(code)
    return code


def get_all_code_c_style(
    stdin_text: str,
    *,
    languages: tuple[str, ...],
) -> str:
    """Like get_all_code but uses the C-style comment/string stripper.

    Use for JS, TS, Go, Rust, C, C++, C#, PHP. Pass the language tags you
    expect in the fenced code blocks (e.g., ("javascript", "js", "typescript", "ts")).
    """
    fence_langs = "|".join(re.escape(lang) for lang in languages)
    pattern = rf"```(?:{fence_langs})?\n(.*?)```"
    blocks = re.findall(pattern, stdin_text, re.DOTALL)
    code = "\n".join(blocks)

    msgs_file = os.environ.get("EVAL_MESSAGES_FILE")
    if msgs_file:
        with open(msgs_file, encoding="utf-8") as f:
            messages = json.load(f)
        code += "\n" + get_written_content(messages)

    return strip_c_style_comments(code)


def fail(msg: str) -> int:
    """Print failure reason to stderr and return exit code 1."""
    print(msg, file=sys.stderr)
    return 1
