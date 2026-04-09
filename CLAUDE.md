# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Evaluation framework for Claude Code skills. Compares Claude's output with and without a skill by running `claude -p`, then scoring via rubric judging, automated checks, and before/after diffs. Python 3.12, Pipenv, zero runtime dependencies (stdlib only).

## Commands

```bash
pipenv install --dev          # Install dependencies
pipenv shell                  # Activate virtualenv
python -m src.cli run         # Run all evaluations
python -m src.cli run --cases "python_style_*"  # Filter by glob
python -m src.cli list        # List test cases
python -m src.cli report --run-id <ID>          # View results
pytest                        # Run tests
ruff check src/ tests/        # Lint
```

## Architecture

`cli.py` orchestrates the pipeline per test case:
1. `runner.py` — invokes `claude -p --bare` (baseline) and `claude -p --append-system-prompt <skill>` (with skill), parses `--output-format json`
2. `scorer.py` — separate judge Claude call with `--json-schema` scores outputs 0-2 per rubric criterion
3. `checker.py` — extracts fenced code blocks, runs linters and check scripts against them
4. `differ.py` — `difflib.unified_diff` + AI summary via Claude call
5. `results.py` — streams rows to TSV files incrementally (partial results survive crashes)

All types and path constants live in `config.py`.

## Adding Test Cases

TOML files in `evals/cases/` — see `python_style_001.toml` for the schema. Check scripts go in `evals/checks/` (receive full output on stdin, exit 0=pass/1=fail, diagnostics to stderr).

## Conventions

- Skills live in `skills/` as markdown files with YAML frontmatter (name, description)
- Results are TSV files in `results/` (gitignored except `.gitkeep`)
- Functional style, no classes — small focused functions
