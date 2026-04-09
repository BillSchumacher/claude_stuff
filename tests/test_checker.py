"""Tests for code block extraction."""

from src.checker import extract_code_blocks


def test_extract_single_block():
    output = "Some text\n```python\ndef foo():\n    pass\n```\nMore text"
    blocks = extract_code_blocks(output)
    assert len(blocks) == 1
    assert "def foo():" in blocks[0]


def test_extract_multiple_blocks():
    output = "```python\nblock1\n```\ntext\n```js\nblock2\n```"
    blocks = extract_code_blocks(output)
    assert len(blocks) == 2
    assert blocks[0].strip() == "block1"
    assert blocks[1].strip() == "block2"


def test_extract_no_blocks():
    output = "Just plain text without any code blocks"
    blocks = extract_code_blocks(output)
    assert blocks == []


def test_extract_unfenced_block():
    output = "```\nno language\n```"
    blocks = extract_code_blocks(output)
    assert len(blocks) == 1
    assert blocks[0].strip() == "no language"
