# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Two things in one repo:

1. **Claude Code plugin marketplace** — `.claude-plugin/marketplace.json` lists plugins under `plugins/`. Each plugin contains skills as `plugins/<plugin>/skills/<skill>/SKILL.md` with YAML frontmatter. Owner: `BillSchumacher`.
2. **Evaluation framework** — Python 3.12 (Pipenv, stdlib only). Runs `claude -p` twice per test case (baseline vs with-skill), captures the full message stream, then scores via rubric judge, automated check scripts, and before/after diffs. Results are TSVs in `results/`.

## Commands

```bash
pipenv install --dev
pipenv run python -m src.cli list                         # list test cases
pipenv run python -m src.cli run                          # run all
pipenv run python -m src.cli run --cases "security_*"     # glob filter
pipenv run python -m src.cli report --run-id <ID>         # view a past run
pipenv run pytest tests/ -v                               # unit tests
```

Eval runs are slow: each case spawns at least 2 `claude -p` invocations plus a judge call and a diff-summary call. Budget 1–5 minutes per case. Use `run_in_background: true` when running suites.

## Plugin marketplace layout

```
.claude-plugin/
  marketplace.json                 # Catalog (name, owner, plugins[])
plugins/
  <plugin-name>/
    .claude-plugin/
      plugin.json                  # name, description, version, author
    skills/
      <skill-name>/
        SKILL.md                   # YAML frontmatter + content
```

Skills are auto-invoked by Claude based on the frontmatter `description`. Critical finding: **the agent only invokes ONE skill by default**, even when multiple match. The `skill-orchestration` plugin is a meta-skill that explicitly instructs the agent to invoke every relevant skill — load it alongside the worker skills if a task should use multiple.

### Adding a new plugin

Prefer the scaffold command — it writes the manifest, skill stub, and marketplace entry in one step, and detects the author from the git remote so contributors get their own attribution automatically:

```bash
pipenv run python -m src.cli new-plugin my-plugin \
  --description "One-line description" \
  [--skill my-skill]  # defaults to the plugin name
  [--author Name]     # override the detected author
```

Author detection (`src/git_meta.py`): parses `git remote get-url origin` — owner segment of github/gitlab/bitbucket/ssh URLs wins. Falls back to `git config user.name`, then to `"unknown"`. The result is cached for the life of the process.

After scaffolding, fill in the SKILL.md rules and (optionally) add eval cases under `evals/cases/`.

## Eval framework architecture

`src/cli.py` orchestrates the pipeline per case:

1. **`runner.py`** — builds the `claude -p` command. Uses `--output-format stream-json --verbose --dangerously-skip-permissions`. Baseline uses `--disable-slash-commands`; with-skill uses repeated `--plugin-dir <abs path>`. Each variant runs in an isolated `tempfile.gettempdir()/skill_eval/<case_id>_<variant>/` directory so they don't contaminate each other. `run_claude()` returns `(text, messages)` — `messages` is the full stream-json message list including all tool_use and tool_result events.
2. **`scorer.py`** — judge call via `run_claude_json()` (separate helper for `--output-format json` calls; **don't use `run_claude` here**, that one is for stream-json). Uses `--append-system-prompt` to instruct the judge to return JSON; the response is parsed by `parse_judge_response()` which handles raw JSON, fenced JSON, and embedded JSON. **Do not use `--json-schema`** — it caused API errors and unreliable formatting. `enrich_with_written_files()` appends `Write` tool contents to the agent's text response before sending to the judge, otherwise the judge only sees a summary and gives unfair partial scores.
3. **`checker.py`** — runs linters and check scripts. Each check script gets the agent's text on stdin plus a JSON file with the full message stream at `$EVAL_MESSAGES_FILE` and a comma-separated `$EVAL_EXPECTED_SKILLS`.
4. **`differ.py`** — `difflib.unified_diff` + an AI-generated diff summary.
5. **`results.py`** — streams rows to TSV incrementally so partial results survive crashes.

`config.py` holds `RunResult(case_id, variant, raw_output, model, timestamp, messages)` and path constants.

## Test case TOML schema

```toml
[case]
id = "unique_id"
name = "Human-readable name"
description = "What the test measures"
plugins = ["plugin-name"]               # Plugins to load via --plugin-dir
expected_skills = ["plugin-name"]       # Optional; defaults to plugins.
                                         # Used by skills_invoked.py check.

[prompt]
text = """Neutral prompt that doesn't mention the skill area."""

[rubric]
criteria = ["Criterion 1", "Criterion 2"]   # Judge scores 0-2 per criterion

[checks]
scripts = ["evals/checks/has_X.py"]
linters = ["ruff check"]                # Optional; runs per code block

[options]
model = "sonnet"                        # or opus, haiku
max_budget_usd = 1.0
timeout_seconds = 600                   # Optional, default 300. Increase for
                                         # open-ended prompts where the baseline
                                         # may run long.
```

## Check script conventions

- Live in `evals/checks/`. Filenames start with `_` for shared helpers (not auto-discovered).
- Receive the agent's text response on stdin. Read `EVAL_MESSAGES_FILE` env var (path to JSON) for the full message stream, and `EVAL_EXPECTED_SKILLS` for the expected skill list.
- Exit 0 = pass, non-zero = fail. Diagnostics to stderr.
- Import `_security_lib` (not security-only despite the name) for `get_all_code()`, `get_written_content()`, `strip_docstrings_and_comments()`, and `fail()`. Use `sys.path.insert(0, str(Path(__file__).parent))` before importing.
- `get_all_code()` strips docstrings, comments, and non-f-string literals by default — patterns inside prose like `"never use verify=False"` won't false-positive. F-strings are preserved so SQL injection detection on f"SELECT..." still works.
- For checks that need to inspect markdown structure (OpenAPI specs, acceptance criteria sections), use `get_written_content()` directly so the strip pass doesn't run.

## Important gotchas

- **`--bare` flag has auth issues**: it skips OAuth/keychain reads and only honors `ANTHROPIC_API_KEY`, so subprocess calls fail with "Not logged in." Use `--disable-slash-commands` instead for clean baselines.
- **The judge sees only the agent's final text response unless we enrich it.** Agents that use `Write` tool calls produce a short summary in `result` and the actual code in tool input. `enrich_with_written_files()` in `scorer.py` fixes this.
- **Stale eval results** between variants: each variant must run in its own working dir. `_make_workdir()` in `runner.py` creates and cleans them.
- **Agent gets confused by `/tmp/` paths on Windows** because of WSL/MSYS path translation. Prefer relative paths or `tempfile.gettempdir()` based dirs.
- **Pyright shows "Import _security_lib could not be resolved"** for check scripts — this is because they use runtime `sys.path` manipulation. Ignore the warning; the imports work at runtime.
- **Open-ended prompts** ("build feature X") cause the baseline to dive into a full implementation and time out. Either increase `timeout_seconds` or constrain the prompt to "describe what you would build" so the eval measures specification quality, not code-writing speed.

## Conventions

- Functional style, no classes. Small focused functions.
- Memory-efficient: stream rows to TSV, don't accumulate.
- Result TSVs are gitignored except `results/.gitkeep`.
- All plugin authors are `BillSchumacher`.
