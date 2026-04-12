"""Read and write evaluation results to a SQLite database."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config import RESULTS_DIR

DB_PATH = RESULTS_DIR / "evals.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT,
    status TEXT DEFAULT 'pending',
    current_case TEXT,
    total_cases INTEGER DEFAULT 0,
    completed_cases INTEGER DEFAULT 0,
    pid INTEGER,
    error TEXT
);

CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    data TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS case_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    model TEXT,
    timestamp TEXT,
    raw_output TEXT,
    messages TEXT,
    command TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    criterion TEXT,
    score INTEGER,
    explanation TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    check_name TEXT,
    passed INTEGER,
    detail TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS diffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    raw_diff TEXT,
    ai_summary TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    skill TEXT,
    baseline_score INTEGER,
    skill_score INTEGER,
    score_delta INTEGER,
    baseline_checks_passed TEXT,
    skill_checks_passed TEXT,
    diff_summary TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
"""


_MIGRATIONS = [
    # Add status tracking columns to runs (may already exist in fresh DBs)
    "ALTER TABLE runs ADD COLUMN status TEXT DEFAULT 'pending'",
    "ALTER TABLE runs ADD COLUMN current_case TEXT",
    "ALTER TABLE runs ADD COLUMN total_cases INTEGER DEFAULT 0",
    "ALTER TABLE runs ADD COLUMN completed_cases INTEGER DEFAULT 0",
    "ALTER TABLE runs ADD COLUMN pid INTEGER",
    "ALTER TABLE runs ADD COLUMN error TEXT",
    "ALTER TABLE case_results ADD COLUMN command TEXT",
    "ALTER TABLE case_results ADD COLUMN input_tokens INTEGER DEFAULT 0",
    "ALTER TABLE case_results ADD COLUMN output_tokens INTEGER DEFAULT 0",
    "ALTER TABLE case_results ADD COLUMN cache_read_tokens INTEGER DEFAULT 0",
    "ALTER TABLE case_results ADD COLUMN cache_creation_tokens INTEGER DEFAULT 0",
    "ALTER TABLE case_results ADD COLUMN cost_usd REAL DEFAULT 0",
]


def _get_db() -> sqlite3.Connection:
    """Open (and initialise if needed) the results database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    # Run migrations — skip any that fail (column already exists)
    for sql in _MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn


def create_run(
    run_id: str,
    started_at: str,
    *,
    status: str = "pending",
    total_cases: int = 0,
    pid: int | None = None,
) -> None:
    with _get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO runs "
            "(run_id, started_at, status, total_cases, pid) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, started_at, status, total_cases, pid),
        )


def update_run_status(
    run_id: str,
    *,
    status: str | None = None,
    current_case: str | None = None,
    completed_cases: int | None = None,
    error: str | None = None,
) -> None:
    sets, vals = [], []
    if status is not None:
        sets.append("status = ?")
        vals.append(status)
    if current_case is not None:
        sets.append("current_case = ?")
        vals.append(current_case)
    if completed_cases is not None:
        sets.append("completed_cases = ?")
        vals.append(completed_cases)
    if error is not None:
        sets.append("error = ?")
        vals.append(error)
    if not sets:
        return
    vals.append(run_id)
    with _get_db() as db:
        db.execute(f"UPDATE runs SET {', '.join(sets)} WHERE run_id = ?", vals)


def get_run_status(run_id: str) -> dict | None:
    with _get_db() as db:
        row = db.execute(
            "SELECT run_id, started_at, status, current_case, "
            "total_cases, completed_cases, pid, error "
            "FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    return dict(row) if row else None


def get_active_run() -> dict | None:
    """Find the most recent run with status 'running' or 'cancelling'."""
    with _get_db() as db:
        row = db.execute(
            "SELECT run_id, started_at, status, current_case, "
            "total_cases, completed_cases, pid, error "
            "FROM runs WHERE status IN ('running', 'cancelling') "
            "ORDER BY started_at DESC LIMIT 1",
        ).fetchone()
    return dict(row) if row else None


def get_all_active_runs() -> list[dict]:
    """Find all runs with status 'running' or 'cancelling'."""
    with _get_db() as db:
        rows = db.execute(
            "SELECT run_id, started_at, status, current_case, "
            "total_cases, completed_cases, pid, error "
            "FROM runs WHERE status IN ('running', 'cancelling') "
            "ORDER BY started_at",
        ).fetchall()
    return [dict(r) for r in rows]


def emit_event(run_id: str, event_type: str, data: dict) -> None:
    with _get_db() as db:
        db.execute(
            "INSERT INTO run_events (run_id, event_type, data) VALUES (?, ?, ?)",
            (run_id, event_type, json.dumps(data, ensure_ascii=False)),
        )


def get_events_since(run_id: str, after_id: int = 0) -> list[dict]:
    with _get_db() as db:
        rows = db.execute(
            "SELECT id, event_type, data FROM run_events "
            "WHERE run_id = ? AND id > ? ORDER BY id",
            (run_id, after_id),
        ).fetchall()
    return [
        {"id": r["id"], "event": r["event_type"], "data": json.loads(r["data"])}
        for r in rows
    ]


def request_cancel(run_id: str) -> bool:
    with _get_db() as db:
        cur = db.execute(
            "UPDATE runs SET status = 'cancelling' "
            "WHERE run_id = ? AND status = 'running'",
            (run_id,),
        )
    return cur.rowcount > 0


def _extract_usage(messages: list[dict]) -> dict:
    """Extract token usage and cost from the final result message."""
    usage = {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_creation_tokens": 0,
        "cost_usd": 0.0,
    }
    for msg in messages:
        if msg.get("type") == "result":
            u = msg.get("usage", {}) or {}
            usage["input_tokens"] = u.get("input_tokens", 0) or 0
            usage["output_tokens"] = u.get("output_tokens", 0) or 0
            usage["cache_read_tokens"] = u.get("cache_read_input_tokens", 0) or 0
            usage["cache_creation_tokens"] = u.get("cache_creation_input_tokens", 0) or 0
            usage["cost_usd"] = msg.get("total_cost_usd", 0.0) or 0.0
            break
    return usage


def save_case_result(
    run_id: str,
    case_id: str,
    variant: str,
    model: str,
    timestamp: str,
    raw_output: str,
    messages: list[dict],
    command: str = "",
) -> None:
    u = _extract_usage(messages)
    with _get_db() as db:
        db.execute(
            "INSERT INTO case_results "
            "(run_id, case_id, variant, model, timestamp, raw_output, messages, command, "
            "input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, cost_usd) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, case_id, variant, model, timestamp,
             raw_output, json.dumps(messages, ensure_ascii=False), command,
             u["input_tokens"], u["output_tokens"],
             u["cache_read_tokens"], u["cache_creation_tokens"], u["cost_usd"]),
        )


def save_scores(run_id: str, rows: list[dict[str, Any]]) -> None:
    with _get_db() as db:
        db.executemany(
            "INSERT INTO scores "
            "(run_id, case_id, variant, criterion, score, explanation) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (run_id, r["case_id"], r["variant"],
                 r["criterion"], r["score"], r["explanation"])
                for r in rows
            ],
        )


def save_checks(run_id: str, rows: list[dict[str, Any]]) -> None:
    with _get_db() as db:
        db.executemany(
            "INSERT INTO checks "
            "(run_id, case_id, variant, check_name, passed, detail) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (run_id, r["case_id"], r["variant"],
                 r["check_name"], int(r["passed"]), r["detail"])
                for r in rows
            ],
        )


def save_diff(run_id: str, case_id: str, raw_diff: str, ai_summary: str) -> None:
    with _get_db() as db:
        db.execute(
            "INSERT INTO diffs (run_id, case_id, raw_diff, ai_summary) "
            "VALUES (?, ?, ?, ?)",
            (run_id, case_id, raw_diff, ai_summary),
        )


def get_diff(run_id: str, case_id: str) -> dict | None:
    with _get_db() as db:
        row = db.execute(
            "SELECT raw_diff, ai_summary FROM diffs "
            "WHERE run_id = ? AND case_id = ?",
            (run_id, case_id),
        ).fetchone()
    return dict(row) if row else None


def save_summary(run_id: str, row: dict[str, Any]) -> None:
    with _get_db() as db:
        db.execute(
            "INSERT INTO summaries "
            "(run_id, case_id, skill, baseline_score, skill_score, "
            "score_delta, baseline_checks_passed, skill_checks_passed, diff_summary) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id, row["case_id"], row["skill"],
                int(row["baseline_score"]), int(row["skill_score"]),
                int(row["score_delta"].replace("+", "")),
                row["baseline_checks_passed"], row["skill_checks_passed"],
                row["diff_summary"],
            ),
        )


def get_summaries(run_id: str) -> list[dict]:
    with _get_db() as db:
        rows = db.execute(
            "SELECT * FROM summaries WHERE run_id = ? ORDER BY case_id",
            (run_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_case_result(run_id: str, case_id: str, variant: str) -> dict | None:
    """Retrieve full case result including command."""
    with _get_db() as db:
        row = db.execute(
            "SELECT model, timestamp, command FROM case_results "
            "WHERE run_id = ? AND case_id = ? AND variant = ?",
            (run_id, case_id, variant),
        ).fetchone()
    return dict(row) if row else None


def get_case_messages(run_id: str, case_id: str, variant: str) -> list[dict]:
    """Retrieve the full message stream for a specific case variant."""
    with _get_db() as db:
        row = db.execute(
            "SELECT messages FROM case_results "
            "WHERE run_id = ? AND case_id = ? AND variant = ?",
            (run_id, case_id, variant),
        ).fetchone()
    if row and row["messages"]:
        return json.loads(row["messages"])
    return []


def get_checks(run_id: str, case_id: str | None = None) -> list[dict]:
    with _get_db() as db:
        if case_id:
            rows = db.execute(
                "SELECT * FROM checks WHERE run_id = ? AND case_id = ? ORDER BY id",
                (run_id, case_id),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM checks WHERE run_id = ? ORDER BY case_id, id",
                (run_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_scores(run_id: str, case_id: str | None = None) -> list[dict]:
    with _get_db() as db:
        if case_id:
            rows = db.execute(
                "SELECT * FROM scores WHERE run_id = ? AND case_id = ? ORDER BY id",
                (run_id, case_id),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM scores WHERE run_id = ? ORDER BY case_id, id",
                (run_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def backfill_token_usage() -> int:
    """Parse messages from existing case_results and populate token columns.

    Only updates rows where tokens are currently zero.  Returns rows updated.
    """
    updated = 0
    with _get_db() as db:
        rows = db.execute(
            "SELECT id, messages FROM case_results "
            "WHERE messages IS NOT NULL AND messages != '' "
            "AND (input_tokens = 0 AND output_tokens = 0 AND cost_usd = 0)",
        ).fetchall()
        for row in rows:
            try:
                msgs = json.loads(row["messages"])
            except (json.JSONDecodeError, ValueError):
                continue
            u = _extract_usage(msgs)
            if u["input_tokens"] or u["output_tokens"] or u["cost_usd"]:
                db.execute(
                    "UPDATE case_results SET "
                    "input_tokens = ?, output_tokens = ?, "
                    "cache_read_tokens = ?, cache_creation_tokens = ?, cost_usd = ? "
                    "WHERE id = ?",
                    (u["input_tokens"], u["output_tokens"],
                     u["cache_read_tokens"], u["cache_creation_tokens"],
                     u["cost_usd"], row["id"]),
                )
                updated += 1
    return updated


def get_usage_by_model() -> dict[str, dict]:
    """Aggregate total token usage and cost per model across all runs."""
    with _get_db() as db:
        rows = db.execute("""
            SELECT model,
                   SUM(input_tokens) as input_tokens,
                   SUM(output_tokens) as output_tokens,
                   SUM(cache_read_tokens) as cache_read_tokens,
                   SUM(cache_creation_tokens) as cache_creation_tokens,
                   SUM(cost_usd) as cost_usd,
                   COUNT(*) as call_count
            FROM case_results
            WHERE model IS NOT NULL AND model != ''
            GROUP BY model
        """).fetchall()
    return {r["model"]: dict(r) for r in rows}


def get_latest_by_case() -> list[dict]:
    """Get the latest result for each (case_id, model) pair with token stats."""
    with _get_db() as db:
        rows = db.execute("""
            SELECT s.case_id, cr.model, s.skill, s.baseline_score, s.skill_score,
                   s.score_delta, s.baseline_checks_passed, s.skill_checks_passed,
                   s.run_id, s.diff_summary,
                   (SELECT COALESCE(SUM(input_tokens + cache_read_tokens + cache_creation_tokens), 0)
                    FROM case_results WHERE run_id = s.run_id AND case_id = s.case_id) as total_input_tokens,
                   (SELECT COALESCE(SUM(output_tokens), 0)
                    FROM case_results WHERE run_id = s.run_id AND case_id = s.case_id) as total_output_tokens,
                   (SELECT COALESCE(SUM(cost_usd), 0)
                    FROM case_results WHERE run_id = s.run_id AND case_id = s.case_id) as total_cost_usd
            FROM summaries s
            JOIN case_results cr
              ON s.run_id = cr.run_id AND s.case_id = cr.case_id AND cr.variant = 'baseline'
            WHERE s.rowid IN (
                SELECT s2.rowid
                FROM summaries s2
                JOIN case_results cr2
                  ON s2.run_id = cr2.run_id AND s2.case_id = cr2.case_id AND cr2.variant = 'baseline'
                GROUP BY s2.case_id, cr2.model
                HAVING s2.run_id = MAX(s2.run_id)
            )
            ORDER BY cr.model, s.case_id
        """).fetchall()
    return [dict(r) for r in rows]


def get_case_usage(run_id: str, case_id: str) -> list[dict]:
    """Get token usage per variant for a specific case run."""
    with _get_db() as db:
        rows = db.execute("""
            SELECT variant, input_tokens, output_tokens,
                   cache_read_tokens, cache_creation_tokens, cost_usd
            FROM case_results
            WHERE run_id = ? AND case_id = ?
            ORDER BY variant
        """, (run_id, case_id)).fetchall()
    return [dict(r) for r in rows]


def list_runs() -> list[dict]:
    with _get_db() as db:
        rows = db.execute(
            "SELECT r.run_id, r.started_at, COUNT(DISTINCT s.case_id) as case_count "
            "FROM runs r LEFT JOIN summaries s ON r.run_id = s.run_id "
            "GROUP BY r.run_id ORDER BY r.run_id DESC",
        ).fetchall()
    return [dict(r) for r in rows]
