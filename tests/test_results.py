"""Tests for TSV read/write functions."""

import tempfile
from pathlib import Path

from src.results import write_rows, append_rows, read_rows


def test_write_and_read_rows():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".tsv", delete=False,
    ) as f:
        path = Path(f.name)

    fields = ["name", "value"]
    rows = [{"name": "a", "value": "1"}, {"name": "b", "value": "2"}]

    count = write_rows(path, fields, iter(rows))
    assert count == 2

    result = list(read_rows(path))
    assert len(result) == 2
    assert result[0] == {"name": "a", "value": "1"}
    assert result[1] == {"name": "b", "value": "2"}

    path.unlink()


def test_append_rows_creates_header():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".tsv", delete=False,
    ) as f:
        path = Path(f.name)
    # Truncate to make it empty
    path.write_text("")

    fields = ["x", "y"]
    count = append_rows(path, fields, iter([{"x": "1", "y": "2"}]))
    assert count == 1

    count = append_rows(path, fields, iter([{"x": "3", "y": "4"}]))
    assert count == 1

    result = list(read_rows(path))
    assert len(result) == 2
    assert result[0] == {"x": "1", "y": "2"}
    assert result[1] == {"x": "3", "y": "4"}

    path.unlink()


def test_tab_separated_format():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".tsv", delete=False,
    ) as f:
        path = Path(f.name)

    fields = ["col1", "col2"]
    write_rows(path, fields, iter([{"col1": "hello", "col2": "world"}]))

    raw = path.read_text(encoding="utf-8")
    lines = raw.strip().split("\n")
    assert lines[0] == "col1\tcol2"
    assert lines[1] == "hello\tworld"

    path.unlink()
