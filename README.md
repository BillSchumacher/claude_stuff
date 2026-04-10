# claude-stuff

A framework for organizing reusable [Claude Code](https://claude.ai/code) skills and evaluating their effectiveness.

## What it does

Skills are markdown files (slash commands, instruction blocks, prompt snippets) that shape Claude Code's behavior. This framework answers the question: **does a skill actually improve Claude's output?**

For each test case, the framework:

1. Runs `claude -p` **without** the skill (baseline)
2. Runs `claude -p` **with** the skill injected
3. Compares the two outputs using three methods:
   - **Rubric scoring** — a judge Claude call rates outputs 0-2 per criterion
   - **Automated checks** — linters and custom scripts validate the output
   - **Before/after diffs** — unified diff with an AI-generated summary

Results are stored as TSV files for easy inspection and analysis.

## Setup

Requires Python 3.12+ and [Pipenv](https://pipenv.pypa.io/). No runtime dependencies beyond stdlib.

```bash
pipenv install --dev
pipenv shell
```

## Usage

```bash
# List available test cases
python -m src.cli list

# Run all evaluations
python -m src.cli run

# Run specific cases by glob pattern
python -m src.cli run --cases "python_style_*"

# Override model or budget
python -m src.cli run --model opus --budget 2.0

# View results
python -m src.cli report --run-id <RUN_ID>
```

## Project structure

```
.claude-plugin/marketplace.json   Plugin marketplace catalog
plugins/                          Skill plugins (loaded via --plugin-dir)
  dev-workflow/                   TDD with Gherkin, code quality, git discipline
  python-style/                   Python conventions (type hints, docstrings, PEP 8)
  secure-coding/                  OWASP Top 10:2025, ASVS 5.0, NIST SSDF
  api-design/                     REST contracts (OpenAPI 3.1, RFC 9457, pagination)
  observability/                  OpenTelemetry, structured logging, SLI/SLO
  acceptance-criteria/            Requirements specification (ISO 29148, BDD)
  skill-orchestration/            Meta-skill for multi-skill invocation
  efficient-code/                 Language-neutral algorithmic efficiency
  efficient-code-{c,cpp,csharp,   Language-specific efficiency (9 languages)
    go,javascript,php,python,
    rust,typescript}/
evals/
  cases/                          Test case definitions (TOML) — 68 cases
  checks/                         Custom check scripts (exit 0=pass, 1=fail)
results/                          TSV output from evaluation runs
src/                              Framework source code
tests/                            Unit tests (18 tests)
```

## Defining test cases

Test cases are TOML files in `evals/cases/`. Example:

```toml
[case]
id = "python_style_001"
name = "CSV line parser with style"
plugins = ["python-style"]            # Plugins to load via --plugin-dir
# expected_skills = ["python-style"]  # Optional: skills the agent should invoke
                                       #   (defaults to `plugins`)

[prompt]
text = """
Write a Python function called `parse_csv_line` that takes a single line
of CSV text and returns a list of fields. Handle quoted fields.
"""

[rubric]
criteria = [
    "Function has a docstring",
    "Has type annotations",
    "Handles quoted fields with commas inside",
]

[checks]
scripts = ["evals/checks/has_docstrings.py"]
linters = ["ruff check"]

[options]
model = "sonnet"
max_budget_usd = 0.5
```

## Custom check scripts

Check scripts in `evals/checks/` receive the full Claude output on stdin. Exit 0 for pass, non-zero for fail. Write diagnostics to stderr.

```python
import sys

def main() -> int:
    output = sys.stdin.read()
    if "def " not in output:
        print("No function definition found", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Output

Each run produces TSV files in `results/`:

- `{run_id}_scores.tsv` — rubric scores per criterion per variant
- `{run_id}_checks.tsv` — pass/fail per check per variant
- `{run_id}_diffs.tsv` — raw diffs and AI summaries
- `{run_id}_summary.tsv` — aggregated per-case comparison

## Findings

### `python-style` improves Python output

**Case:** `python_style_001` — ask Claude to write a CSV line parser, no style hints in the prompt.

| Check / Score | Baseline | With `python-style` |
|---|---|---|
| Rubric score (0-10) | 7 | 9 (+2) |
| `ruff check` | ✅ | ✅ |
| `has_docstrings` | ❌ | ✅ |

The skill consistently adds Google-style docstrings and type annotations that the baseline omits.

### `python-style` causes streaming when the prompt doesn't ask for it

**Case:** `streaming_csv_to_json_001` — ask for a "function that converts a CSV file to JSON", with no mention of streaming or memory efficiency.

| Check / Score | Baseline | With `python-style` |
|---|---|---|
| Rubric score (0-10) | 6 | 10 (+4) |
| `uses_streaming` | ❌ | ✅ |
| `has_docstrings` | ✅ | ✅ |

Without the skill, Claude loads all rows into a list and dumps once. With the skill, Claude streams rows incrementally and writes JSON on the fly — even though the prompt never mentions memory or streaming.

### `dev-workflow` causes real TDD execution, verified from the message stream

**Case:** `dev_workflow_tdd_001` — "Create a Stack data structure. Write the implementation and tests as separate files, then run the tests."

The `tdd_order` check inspects the stream-json message history and classifies each tool call into a TDD event sequence:

| Variant | Tool sequence |
|---|---|
| Baseline | `[write_impl, write_test, run_test_pass]` ❌ impl-first |
| With `dev-workflow` | `[write_test, run_test_fail, write_impl, run_test_pass]` ✅ full TDD cycle |

The skill makes Claude write tests first, **run them and watch them fail** (proving they exercise something), then write the implementation, then re-run.

### Multiple skills are NOT used by default — `skill-orchestration` fixes this

**Case:** `combined_skills_001` — ask for a Queue implementation with both `dev-workflow` and `python-style` available as plugins.

By default, Claude only invokes ONE skill even when multiple are relevant:

```
Skills invoked: ['python-style']
Expected but missing: ['dev-workflow']
```

Adding the `skill-orchestration` meta-skill (case `orchestrated_skills_001`) flips this:

| Check | Baseline | + `dev-workflow` + `python-style` | + `skill-orchestration` |
|---|---|---|---|
| `has_tests` | ✅ | ✅ | ✅ |
| `has_gherkin` | ❌ | ❌ | ✅ |
| `tdd_order` (full cycle) | ❌ | ❌ | ✅ |
| `skills_invoked` (both) | ❌ | ❌ (only python-style) | ✅ (all 3) |

With the orchestrator, the agent invokes `combine-skills`, which routes to **both** worker skills, and the resulting code follows TDD discipline AND has type annotations and docstrings.

**Takeaway:** Just making skills available isn't enough — the agent gravitates toward a single best-match skill by default. A meta-skill that explicitly instructs "invoke every relevant skill, not just one" reliably enables multi-skill composition.

## Full suite results (68 cases)

Run ID `20260410_060431` — all 68 cases, Opus 4.6 judge, Sonnet agent.

**Total rubric: 316 → 372 (+56)**

| Metric | Count |
|---|---|
| Cases | 68 |
| Improved (rubric) | 19 |
| Flat | 46 |
| Degraded | 3 |

### Positive check flips (skill fixed what baseline missed)

| Case | Baseline | With skill | What changed |
|---|---|---|---|
| `dev_workflow_tdd` | 1/3 | 3/3 | Full TDD cycle: write_test → run_fail → write_impl → run_pass |
| `efficiency_tag_filter_typescript` | 0/1 | 1/1 | `.every(t => arr.includes(t))` → `Set.has()` |
| `refactor_nested_loop_c` | 0/1 | 1/1 | Nested `for` with `==` → `qsort` + adjacent scan |
| `refactor_string_concat_go` | 0/1 | 1/1 | `string +=` in loop → `strings.Builder` |
| `orchestrated_skills` | 1/4 | 4/4 | Meta-skill caused invocation of both `dev-workflow` and `python-style` |
| `sdlc_observability` | 0/1 | 1/1 | Added OpenTelemetry spans + structured logging |

### Top rubric improvements

| Case | Category | Δ |
|---|---|---|
| `sdlc_observability` | Observability | +9 |
| `efficiency_dedup_c` | Efficiency (C) | +6 |
| `orchestrated_skills` | Multi-skill | +6 |
| `refactor_includes_loop_js` | Efficiency (JS) | +4 |
| `refactor_nested_loop_c` | Efficiency (C) | +4 |
| `sdlc_api_design` | API design | +4 |
| `security_request_logger` | Security | +4 |
| `streaming_csv_to_json` | Python style | +4 |
| `dev_workflow_tdd` | Dev workflow | +3 |
| `efficiency_log_report_rust` | Efficiency (Rust) | +3 |

### Degraded cases

| Case | Baseline | With skill | Δ | Issue |
|---|---|---|---|---|
| `efficiency_find_cheapest_go` | 1/1 | 0/1 | -1 | `no_sorted_for_minmax` check uses Python regex on Go code — false positive |
| `efficiency_stair_climbing_js` | 1/1 | 0/1 | 0 | `no_naive_recursion` check matches JS function names incorrectly when the skill variant uses a different recursion pattern |
| `efficiency_word_count_php` | 1/1 | 0/1 | 0 | `no_double_lookup` check uses Python dict syntax (`if k in d: d[k]`) which doesn't match PHP — false positive on PHP code |
| `efficiency_event_count_cpp` | — | — | -1 | Rubric noise: both use `const auto&`, skill variant's prose scored slightly lower |
| `sdlc_acceptance_criteria` | — | — | -3 | Non-deterministic: with-skill variant asked clarifying questions instead of producing spec (correct per skill, but scored lower) |
| `python_style_001` | 1/2 | 0/2 | +1 | `ruff`/`has_docstrings` check regressed while rubric improved — check scripts matched against agent prose not just code |

**Root cause for negative check flips:** Three of the check scripts (`no_sorted_for_minmax`, `no_naive_recursion`, `no_double_lookup`) were written for Python and use Python-specific regex patterns. When applied to Go, JavaScript, or PHP output, they produce false positives. These checks need language-aware variants or should be restricted to Python-only cases.

### Results by skill category

| Category | Cases | Rubric Δ | Positive check flips |
|---|---|---|---|
| Efficiency (from-scratch) | 18 | +9 | 1 (tag filter TS) |
| Efficiency (extend-existing) | 9 | +14 | 2 (nested loop C, string concat Go) |
| Efficiency (review) | 9 | +3 | 0 |
| Efficiency (new rule coverage) | 16 | +2 | 0 |
| Security | 8 | +6 | 0 |
| SDLC | 3 | +10 | 1 (observability) |
| Dev workflow + orchestration | 3 | +9 | 2 (TDD, multi-skill) |
| Python style + streaming | 2 | +5 | 0 |

### Key takeaways

1. **Skills have the most impact on SDLC practices** (observability +9, API design +4, TDD +3) and **extend-existing-code tasks** (total +14 across 9 cases). These are the tasks where the baseline produces functional-but-incomplete code and the skill adds production-readiness.

2. **Security and efficiency skills are hardening passes.** Modern Sonnet already avoids flagrant anti-patterns (SQL injection, `pickle`, `list.pop(0)`, nested loops for dedup). The skills add defense-in-depth, complexity analysis, and stdlib-specific optimizations that the baseline omits.

3. **The "extend inefficient code" paradigm is the best discriminator** for efficiency skills. Giving the agent existing inefficient code and asking it to build on it reveals whether the skill overrides the "copy the existing pattern" impulse. The Go `string +=` and C nested-loop cases flip reliably.

4. **Multi-skill orchestration requires the `skill-orchestration` meta-skill.** Without it, the agent invokes only one skill even when multiple are relevant. With it, all relevant skills are invoked and their guidance composes.

5. **Check scripts designed for one language produce false positives on others.** Three negative check flips trace to Python-centric regex being applied to Go/JS/PHP output. Language-specific checks should be restricted to their target language.
