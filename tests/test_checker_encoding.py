"""Tests that the checker pipeline handles non-ASCII characters (emojis, em-dashes, smart quotes)."""

from src.checker import run_check_script
from src.config import ROOT


SCRIPT = ROOT / "evals" / "checks" / "no_sort_for_topk.py"


def _output_with_unicode() -> str:
    # Includes: beer emoji, em-dash, smart quotes, CJK, combining accent
    return (
        "```python\n"
        "# Top-5 report 🍺 — uses \u201cheapq\u201d for efficiency\n"
        "# 中文注释 café\n"
        "import heapq\n"
        "top5 = heapq.nlargest(5, items)\n"
        "```\n"
    )


def test_check_script_handles_emoji_and_emdash():
    """Regression test: a check script must not crash when the agent's output
    contains emojis, em-dashes, smart quotes, or other non-ASCII characters.
    Before the fix, subprocess defaulted to cp1252 on Windows and crashed."""
    row = run_check_script(
        _output_with_unicode(),
        SCRIPT,
        case_id="test_encoding",
        variant="baseline",
        messages=None,
        expected_skills=None,
    )
    assert row["passed"] is True
    assert "decode" not in row["detail"].lower()
    assert "codec" not in row["detail"].lower()


def test_check_script_handles_unicode_in_messages_file():
    """The messages file written for EVAL_MESSAGES_FILE must also be utf-8 safe."""
    messages = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Write",
                        "input": {
                            "file_path": "/tmp/héllo.py",
                            "content": "# 🎉 emoji — comment\nimport heapq\nx = heapq.nlargest(3, xs)\n",
                        },
                    }
                ]
            },
        }
    ]
    row = run_check_script(
        _output_with_unicode(),
        SCRIPT,
        case_id="test_encoding_msgs",
        variant="baseline",
        messages=messages,
    )
    assert row["passed"] is True
    assert "decode" not in row["detail"].lower()
