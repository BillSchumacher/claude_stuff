"""Read and write evaluation results as TSV files."""

import csv
from pathlib import Path
from typing import Iterator, Any

from src.config import RESULTS_DIR

def _writer(f: Any, fieldnames: list[str]) -> csv.DictWriter[str]:
    return csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")


def write_rows(
    path: Path,
    fieldnames: list[str],
    rows: Iterator[dict[str, Any]],
) -> int:
    """Write rows to a TSV file with headers. Returns count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = _writer(f, fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def append_rows(
    path: Path,
    fieldnames: list[str],
    rows: Iterator[dict[str, Any]],
) -> int:
    """Append rows to an existing TSV, writing header if file is new. Returns count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    count = 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = _writer(f, fieldnames)
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def read_rows(path: Path) -> Iterator[dict[str, str]]:
    """Read rows from a TSV file, yielding dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f, delimiter="\t")


def scores_path(run_id: str) -> Path:
    return RESULTS_DIR / f"{run_id}_scores.tsv"


def checks_path(run_id: str) -> Path:
    return RESULTS_DIR / f"{run_id}_checks.tsv"


def diffs_path(run_id: str) -> Path:
    return RESULTS_DIR / f"{run_id}_diffs.tsv"


def summary_path(run_id: str) -> Path:
    return RESULTS_DIR / f"{run_id}_summary.tsv"
