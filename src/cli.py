"""CLI entry point for the evaluation framework."""

import argparse
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import EVALS_DIR, ROOT
from src.runner import run_case
from src.scorer import score_pair
from src.checker import check_output
from src.differ import diff_pair
from src import results
from src.plugin_scaffold import scaffold_plugin
from src.git_meta import get_author


def load_case(path: Path) -> dict[str, Any]:
    """Parse a TOML test case file."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def discover_cases(pattern: str | None = None) -> list[Path]:
    """Find test case TOML files matching an optional glob pattern."""
    glob = pattern or "*.toml"
    return sorted(EVALS_DIR.glob(glob))


def run_eval(
    case_path: Path,
    run_id: str,
    *,
    model: str = "sonnet",
    model_override: bool = False,
    max_budget_usd: float = 0.5,
    on_message=None,
    on_judge_message=None,
) -> dict[str, Any]:
    """Run a single evaluation case through the full pipeline.

    model_override: if True, the model parameter takes precedence over TOML.
    on_message: if provided, called with (variant, msg) for live streaming.
    Saves all results (including full message streams) to SQLite.
    Returns a dict with summary data for console output.
    """
    case = load_case(case_path)
    case_id = case["case"]["id"]
    plugins = case["case"].get("plugins", [])
    if not plugins and "skill" in case["case"]:
        plugins = [Path(case["case"]["skill"]).stem.replace("_", "-")]
    expected_skills = case["case"].get("expected_skills", plugins)
    prompt = case["prompt"]["text"]
    criteria = case.get("rubric", {}).get("criteria", [])
    checks_cfg = case.get("checks", {})
    linters = checks_cfg.get("linters", [])
    scripts = [Path(s) for s in checks_cfg.get("scripts", [])]
    opts = case.get("options", {})
    case_model = model if model_override else opts.get("model", model)
    case_budget = opts.get("max_budget_usd", max_budget_usd)
    case_timeout = opts.get("timeout_seconds", 300)

    fixture_src = case.get("fixtures", {}).get("source")
    fixture_dir = (ROOT / fixture_src) if fixture_src else None

    with_skill, baseline = run_case(
        prompt, plugins, case_id,
        model=case_model, max_budget_usd=case_budget,
        timeout_seconds=case_timeout,
        fixture_dir=fixture_dir,
        on_message=on_message,
    )

    # Save full message streams
    results.save_case_result(
        run_id, baseline.case_id, baseline.variant,
        baseline.model, baseline.timestamp,
        baseline.raw_output, baseline.messages,
        command=baseline.command,
    )
    results.save_case_result(
        run_id, with_skill.case_id, with_skill.variant,
        with_skill.model, with_skill.timestamp,
        with_skill.raw_output, with_skill.messages,
        command=with_skill.command,
    )

    # Score against rubric
    score_rows = []
    if criteria:
        score_result = score_pair(
            prompt, with_skill, baseline, criteria, model=case_model,
            on_judge_message=on_judge_message,
        )
        score_rows = score_result["rows"]
        if score_rows:
            results.save_scores(run_id, score_rows)
        # Save judge message streams for inspection
        now = datetime.now(timezone.utc).isoformat()
        for jr in score_result["judge_runs"]:
            results.save_case_result(
                run_id, case_id, jr["variant"],
                case_model, now,
                jr["raw_output"], jr["messages"],
                command=jr["command"],
            )

    # Run checks
    check_rows_baseline = list(check_output(
        baseline, linters, scripts, expected_skills=expected_skills,
    ))
    check_rows_skill = list(check_output(
        with_skill, linters, scripts, expected_skills=expected_skills,
    ))
    all_check_rows = check_rows_baseline + check_rows_skill
    if all_check_rows:
        results.save_checks(run_id, all_check_rows)

    # Diff
    diff_data = diff_pair(
        baseline, with_skill, prompt, model=case_model,
        on_judge_message=on_judge_message,
    )
    results.save_diff(run_id, case_id, diff_data["raw_diff"], diff_data["summary"])
    # Save the diff judge's messages too
    now = datetime.now(timezone.utc).isoformat()
    results.save_case_result(
        run_id, case_id, "judge:diff",
        case_model, now,
        diff_data["summary"], diff_data["judge_messages"],
        command=diff_data["judge_command"],
    )

    # Compute summary
    baseline_total = sum(r["score"] for r in score_rows if r["variant"] == "baseline")
    skill_total = sum(r["score"] for r in score_rows if r["variant"] == "with_skill")
    baseline_passed = sum(1 for r in check_rows_baseline if r["passed"])
    skill_passed = sum(1 for r in check_rows_skill if r["passed"])
    total_checks = len(linters) + len(scripts)

    summary_row = {
        "case_id": case_id,
        "skill": ",".join(plugins),
        "baseline_score": str(baseline_total),
        "skill_score": str(skill_total),
        "score_delta": f"{skill_total - baseline_total:+d}",
        "baseline_checks_passed": f"{baseline_passed}/{total_checks}" if total_checks else "n/a",
        "skill_checks_passed": f"{skill_passed}/{total_checks}" if total_checks else "n/a",
        "diff_summary": diff_data["summary"],
    }
    results.save_summary(run_id, summary_row)

    return {"summary": summary_row, "checks": all_check_rows}


def cmd_run(args: argparse.Namespace) -> int:
    """Execute evaluations."""
    cases = discover_cases(args.cases)
    if not cases:
        print("No test cases found.", file=sys.stderr)
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    started_at = datetime.now(timezone.utc).isoformat()
    results.create_run(run_id, started_at)

    print(f"Run ID: {run_id}")
    print(f"Cases: {len(cases)}")

    for case_path in cases:
        case_name = case_path.stem
        print(f"\nRunning: {case_name}...")
        try:
            result = run_eval(
                case_path, run_id,
                model=args.model, max_budget_usd=args.budget,
            )
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            continue

        s = result["summary"]
        print(f"  Score: {s['baseline_score']} -> {s['skill_score']} ({s['score_delta']})")
        print(f"  Checks: {s['baseline_checks_passed']} -> {s['skill_checks_passed']}")

        for check in result["checks"]:
            variant = check["variant"]
            name = check["check_name"]
            passed = "PASS" if check["passed"] else "FAIL"
            detail = check.get("detail", "")[:120]
            print(f"    [{variant:10s}] {passed} {name}  {detail}")

    print(f"\nResults saved to: {results.DB_PATH}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List available test cases."""
    cases = discover_cases()
    if not cases:
        print("No test cases found.")
        return 0

    for path in cases:
        case = load_case(path)
        case_id = case["case"]["id"]
        name = case["case"].get("name", "")
        plugins = case["case"].get("plugins", [])
        if not plugins and "skill" in case["case"]:
            plugins = [case["case"]["skill"]]
        print(f"{case_id}\t{name}\t{','.join(plugins)}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Print summary for a run from the database."""
    rows = results.get_summaries(args.run_id)
    if not rows:
        print(f"No results found for run: {args.run_id}", file=sys.stderr)
        return 1

    for row in rows:
        delta = row["score_delta"]
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        print(f"Case: {row['case_id']}")
        print(f"  Skill: {row['skill']}")
        print(f"  Score: {row['baseline_score']} -> {row['skill_score']} ({delta_str})")
        print(f"  Checks: {row['baseline_checks_passed']} -> {row['skill_checks_passed']}")
        print(f"  Summary: {row['diff_summary']}")

        # Show per-check details
        checks = results.get_checks(args.run_id, row["case_id"])
        if checks:
            for c in checks:
                passed = "PASS" if c["passed"] else "FAIL"
                detail = (c.get("detail") or "")[:120]
                print(f"    [{c['variant']:10s}] {passed} {c['check_name']}  {detail}")
        print()
    return 0


def cmd_new_plugin(args: argparse.Namespace) -> int:
    """Scaffold a new plugin in the marketplace with the author detected from git."""
    author = args.author or get_author()
    skill_name = args.skill or args.name
    created = scaffold_plugin(
        plugin_name=args.name,
        skill_name=skill_name,
        description=args.description,
        author=author,
        version=args.version,
    )
    print(f"Created plugin '{args.name}' (author: {author})")
    print(f"  manifest:    {created['manifest']}")
    print(f"  skill stub:  {created['skill']}")
    print(f"  registered:  {created['marketplace']}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the results web viewer."""
    from src.server import main as serve_main
    serve_main(port=args.port, watch=args.watch)
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    """List all evaluation runs."""
    runs = results.list_runs()
    if not runs:
        print("No runs found.")
        return 0

    for r in runs:
        print(f"{r['run_id']}  {r['started_at']}  cases={r['case_count']}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="skill-eval",
        description="Evaluate Claude Code skills",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run evaluations")
    run_parser.add_argument(
        "--cases", default=None,
        help="Glob pattern to filter cases (e.g. 'formatting_*')",
    )
    run_parser.add_argument("--model", default="sonnet", help="Model to use")
    run_parser.add_argument(
        "--budget", type=float, default=0.5,
        help="Max USD budget per invocation",
    )

    sub.add_parser("list", help="List available test cases")
    sub.add_parser("runs", help="List all evaluation runs")

    serve_parser = sub.add_parser("serve", help="Start web viewer for results")
    serve_parser.add_argument(
        "--port", type=int, default=8000,
        help="Port to serve on (default: 8000)",
    )
    serve_parser.add_argument(
        "--watch", action="store_true",
        help="Auto-restart server when src/*.py files change",
    )

    report_parser = sub.add_parser("report", help="View results")
    report_parser.add_argument("--run-id", required=True, help="Run ID to display")

    new_parser = sub.add_parser(
        "new-plugin",
        help="Scaffold a new plugin in the marketplace (author detected from git remote)",
    )
    new_parser.add_argument("name", help="Plugin name (kebab-case)")
    new_parser.add_argument(
        "--description", required=True,
        help="One-line description used in plugin.json, marketplace.json, and SKILL.md frontmatter",
    )
    new_parser.add_argument(
        "--skill", default=None,
        help="Skill name (defaults to the plugin name)",
    )
    new_parser.add_argument(
        "--author", default=None,
        help="Override the author (by default, detected from git remote)",
    )
    new_parser.add_argument("--version", default="0.1.0", help="Initial version")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    commands = {
        "run": cmd_run,
        "list": cmd_list,
        "runs": cmd_runs,
        "serve": cmd_serve,
        "report": cmd_report,
        "new-plugin": cmd_new_plugin,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
