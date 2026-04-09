"""CLI entry point for the evaluation framework."""

import argparse
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import EVALS_DIR, RESULTS_DIR
from src.runner import run_case
from src.scorer import score_pair
from src.checker import check_output
from src.differ import diff_pair
from src import results

SCORE_FIELDS = ["case_id", "variant", "criterion", "score", "explanation"]
CHECK_FIELDS = ["case_id", "variant", "check_name", "passed", "detail"]
DIFF_FIELDS = ["case_id", "raw_diff", "ai_summary"]
SUMMARY_FIELDS = [
    "case_id", "skill", "baseline_score", "skill_score",
    "score_delta", "baseline_checks_passed", "skill_checks_passed",
    "diff_summary",
]


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
    *,
    model: str = "sonnet",
    max_budget_usd: float = 0.5,
) -> dict[str, Any]:
    """Run a single evaluation case through the full pipeline.

    Returns a dict with scores, checks, diff, and summary data.
    """
    case = load_case(case_path)
    case_id = case["case"]["id"]
    plugins = case["case"].get("plugins", [])
    if not plugins and "skill" in case["case"]:
        # Backwards compat: derive plugin name from old skill path
        plugins = [Path(case["case"]["skill"]).stem.replace("_", "-")]
    prompt = case["prompt"]["text"]
    criteria = case.get("rubric", {}).get("criteria", [])
    checks_cfg = case.get("checks", {})
    linters = checks_cfg.get("linters", [])
    scripts = [Path(s) for s in checks_cfg.get("scripts", [])]
    opts = case.get("options", {})
    case_model = opts.get("model", model)
    case_budget = opts.get("max_budget_usd", max_budget_usd)

    with_skill, baseline = run_case(
        prompt, plugins, case_id,
        model=case_model, max_budget_usd=case_budget,
    )

    score_rows = list(score_pair(
        prompt, with_skill, baseline, criteria, model=case_model,
    )) if criteria else []

    check_rows_baseline = list(check_output(
        baseline, linters, scripts, expected_skills=plugins,
    ))
    check_rows_skill = list(check_output(
        with_skill, linters, scripts, expected_skills=plugins,
    ))
    all_check_rows = check_rows_baseline + check_rows_skill

    diff_data = diff_pair(baseline, with_skill, prompt, model=case_model)

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

    diff_row = {
        "case_id": case_id,
        "raw_diff": diff_data["raw_diff"],
        "ai_summary": diff_data["summary"],
    }

    return {
        "scores": score_rows,
        "checks": all_check_rows,
        "diff": diff_row,
        "summary": summary_row,
    }


def cmd_run(args: argparse.Namespace) -> int:
    """Execute evaluations."""
    cases = discover_cases(args.cases)
    if not cases:
        print("No test cases found.", file=sys.stderr)
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"Run ID: {run_id}")
    print(f"Cases: {len(cases)}")

    for case_path in cases:
        case_name = case_path.stem
        print(f"\nRunning: {case_name}...")
        try:
            result = run_eval(
                case_path, model=args.model, max_budget_usd=args.budget,
            )
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            continue

        results.append_rows(
            results.scores_path(run_id), SCORE_FIELDS,
            iter(result["scores"]),
        )
        results.append_rows(
            results.checks_path(run_id), CHECK_FIELDS,
            iter(result["checks"]),
        )
        results.append_rows(
            results.diffs_path(run_id), DIFF_FIELDS,
            iter([result["diff"]]),
        )
        results.append_rows(
            results.summary_path(run_id), SUMMARY_FIELDS,
            iter([result["summary"]]),
        )

        s = result["summary"]
        print(f"  Score: {s['baseline_score']} -> {s['skill_score']} ({s['score_delta']})")
        print(f"  Checks: {s['baseline_checks_passed']} -> {s['skill_checks_passed']}")

    print(f"\nResults written to: {RESULTS_DIR / run_id}_*.tsv")
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
    """Print summary from a results TSV."""
    path = results.summary_path(args.run_id)
    if not path.exists():
        print(f"No results found for run: {args.run_id}", file=sys.stderr)
        return 1

    rows = list(results.read_rows(path))
    for row in rows:
        print(f"Case: {row['case_id']}")
        print(f"  Skill: {row['skill']}")
        print(f"  Score: {row['baseline_score']} -> {row['skill_score']} ({row['score_delta']})")
        print(f"  Checks: {row['baseline_checks_passed']} -> {row['skill_checks_passed']}")
        print(f"  Summary: {row['diff_summary']}")
        print()
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

    report_parser = sub.add_parser("report", help="View results")
    report_parser.add_argument("--run-id", required=True, help="Run ID to display")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    commands = {"run": cmd_run, "list": cmd_list, "report": cmd_report}
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
