"""Tests for SQLite results storage."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src import results


def _use_temp_db():
    """Patch DB_PATH to a temporary file for isolated tests."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return patch.object(results, "DB_PATH", Path(tmp.name))


def test_create_run_and_list():
    with _use_temp_db():
        results.create_run("20260101_000000", "2026-01-01T00:00:00Z")
        runs = results.list_runs()
        assert len(runs) == 1
        assert runs[0]["run_id"] == "20260101_000000"


def test_save_and_get_summaries():
    with _use_temp_db():
        results.create_run("run1", "2026-01-01T00:00:00Z")
        results.save_summary("run1", {
            "case_id": "test_001",
            "skill": "secure-coding",
            "baseline_score": "8",
            "skill_score": "10",
            "score_delta": "+2",
            "baseline_checks_passed": "2/3",
            "skill_checks_passed": "3/3",
            "diff_summary": "Skill added rate limiting.",
        })

        rows = results.get_summaries("run1")
        assert len(rows) == 1
        assert rows[0]["case_id"] == "test_001"
        assert rows[0]["baseline_score"] == 8
        assert rows[0]["skill_score"] == 10
        assert rows[0]["score_delta"] == 2


def test_save_and_get_case_messages():
    with _use_temp_db():
        results.create_run("run1", "2026-01-01T00:00:00Z")
        messages = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello"}]}},
            {"type": "result", "result": "done"},
        ]
        results.save_case_result(
            "run1", "test_001", "baseline",
            "sonnet", "2026-01-01T00:00:00Z",
            "hello world", messages,
        )

        retrieved = results.get_case_messages("run1", "test_001", "baseline")
        assert len(retrieved) == 2
        assert retrieved[0]["type"] == "assistant"
        assert retrieved[1]["result"] == "done"


def test_save_and_get_checks():
    with _use_temp_db():
        results.create_run("run1", "2026-01-01T00:00:00Z")
        results.save_checks("run1", [
            {"case_id": "test_001", "variant": "baseline",
             "check_name": "no_sql_injection.py", "passed": True, "detail": ""},
            {"case_id": "test_001", "variant": "baseline",
             "check_name": "has_threat_model.py", "passed": False, "detail": "Missing"},
        ])

        checks = results.get_checks("run1", "test_001")
        assert len(checks) == 2
        assert checks[0]["passed"] == 1  # SQLite stores as int
        assert checks[1]["passed"] == 0


def test_save_and_get_scores():
    with _use_temp_db():
        results.create_run("run1", "2026-01-01T00:00:00Z")
        results.save_scores("run1", [
            {"case_id": "test_001", "variant": "with_skill",
             "criterion": "Uses parameterized queries", "score": 2,
             "explanation": "All queries parameterized"},
        ])

        scores = results.get_scores("run1", "test_001")
        assert len(scores) == 1
        assert scores[0]["score"] == 2
        assert scores[0]["criterion"] == "Uses parameterized queries"
