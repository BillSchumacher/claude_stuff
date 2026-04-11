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
  ci-cd/                           CI/CD pipeline best practices (core)
  ci-cd-{cpp,csharp,go,            Language-specific CI/CD (7 languages)
    javascript,php,python,rust}/
  sql/                             SQL best practices (core)
  sql-{mysql,postgresql,           Dialect-specific SQL (4 dialects)
    oracle,mssql}/
evals/
  cases/                          Test case definitions (TOML) — 170 cases
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

| Metric | Baseline | With skills |
|---|---|---|
| Rubric score | 7 | 13 (+6) |
| Checks passed | 3/6 | 6/6 |

| Check | Baseline | With `skill-orchestration` |
|---|---|---|
| `has_tests` | ✅ | ✅ |
| `has_gherkin` | ❌ | ✅ |
| `tdd_order` (full cycle) | ❌ | ✅ |
| `no_sql_injection` | ✅ | ✅ |
| `no_weak_crypto` | ❌ | ✅ |
| `skills_invoked` (all expected) | ✅ | ✅ |

With the orchestrator, the agent invokes `combine-skills`, which routes to **all** relevant worker skills, and the resulting code follows TDD discipline, has type annotations and docstrings, uses parameterized queries, and hashes passwords securely.

**Takeaway:** Just making skills available isn't enough — the agent gravitates toward a single best-match skill by default. A meta-skill that explicitly instructs "invoke every relevant skill, not just one" reliably enables multi-skill composition.

## Full suite results (170 cases)

Opus 4.6 judge, Sonnet agent.

**Total rubric: 922 → 1135 (+213)**

| Metric | Count |
|---|---|
| Cases | 170 |
| Improved (rubric) | 70 |
| Flat | 85 |
| Degraded | 5 |
| Failed (timeout/error) | 10 |
| Failed (judge error) | 2 |

### Positive check flips (skill fixed what baseline missed)

| Case | Baseline | With skill | What changed |
|---|---|---|---|
| `dev_workflow_tdd` | 1/3 | 3/3 | Full TDD cycle: write_test → run_fail → write_impl → run_pass |
| `efficiency_tag_filter_typescript` | 0/1 | 1/1 | `.every(t => arr.includes(t))` → `Set.has()` |
| `refactor_nested_loop_c` | 0/1 | 1/1 | Nested `for` with `==` → `qsort` + adjacent scan |
| `refactor_string_concat_go` | 0/1 | 1/1 | `string +=` in loop → `strings.Builder` |
| `orchestrated_skills` | 3/6 | 6/6 | Meta-skill caused invocation of all expected skills; added Gherkin, TDD cycle, secure crypto |
| `sdlc_observability` | 0/1 | 1/1 | Added OpenTelemetry spans + structured logging |
| `security_headers` | 0/2 | 2/2 | Baseline skips security headers entirely; skill adds CSP, X-Content-Type-Options, HSTS |
| `cicd_python` | 0/3 | 3/3 | Baseline has no caching, coverage, or linting; skill adds all three |
| `cicd_go` | 0/3 | 3/3 | Same — skill adds Go module caching, coverprofile, golangci-lint |
| `cicd_csharp` | 0/3 | 3/3 | Same — skill adds NuGet caching, coverlet, dotnet format |
| `cicd_cpp` | 0/3 | 3/3 | Same — skill adds ccache, gcov coverage, cppcheck |
| `cicd_javascript` | 1/3 | 3/3 | Baseline had linting only; skill adds npm caching and vitest coverage |
| `sql_pagination` | 0/1 | 1/1 | Baseline uses OFFSET; skill uses keyset pagination |
| `sql_mysql_upsert` | 0/1 | 1/1 | Baseline uses SELECT-then-INSERT; skill uses ON DUPLICATE KEY UPDATE |
| `sql_pg_jsonb` | 0/1 | 1/1 | Baseline uses JSON; skill uses JSONB with GIN index |
| `sql_mssql_schema` | 1/2 | 2/2 | Skill adds DATETIME2 and NVARCHAR where baseline used DATETIME/VARCHAR |

### Top rubric improvements

| Case | Category | Δ |
|---|---|---|
| `cicd_python` | CI/CD | +13 |
| `cicd_go` | CI/CD | +9 |
| `sdlc_observability` | Observability | +9 |
| `security_headers` | Security | +9 |
| `pkg_asp_net_di` | Package (ASP.NET) | +8 |
| `cicd_gotcha_rust_incremental` | CI/CD | +8 |
| `efficiency_dedup_c` | Efficiency (C) | +6 |
| `orchestrated_skills` | Multi-skill | +6 |
| `security_request_logger` | Security | +5 |
| `refactor_includes_loop_js` | Efficiency (JS) | +4 |
| `refactor_nested_loop_c` | Efficiency (C) | +4 |
| `sdlc_api_design` | API design | +4 |
| `streaming_csv_to_json` | Python style | +4 |
| `security_error_handling` | Security | +3 |
| `dev_workflow_tdd` | Dev workflow | +3 |
| `efficiency_log_report_rust` | Efficiency (Rust) | +3 |

### Degraded cases (fixed)

Six cases showed degradation in the initial run. Root causes and fixes:

| Case | Issue | Fix |
|---|---|---|
| `efficiency_find_cheapest_go` | `no_sorted_for_minmax` used Python regex on Go code — false positive | Made multi-language: detects Go `sort.Slice` + `[0]` pattern; requires language tag to skip bare blocks with anti-pattern examples |
| `efficiency_stair_climbing_js` | `no_naive_recursion` split on function name, caught test calls as "recursion" | Rewrote with brace-counting for JS function scope; added arrow function support |
| `efficiency_word_count_php` | `no_double_lookup` used Python `if k in d:` pattern on PHP code | Added PHP patterns: `isset`/`array_key_exists` + separate access, suggests `??`/`??=` |
| `efficiency_event_count_cpp` | Rubric noise: both variants use `const auto&`, prose scored -1 | No fix needed — inherent LLM judging variance |
| `sdlc_acceptance_criteria` | Agent asked clarifying questions instead of producing spec | Prompt now says "assume reasonable defaults, note them explicitly"; rubric rewards noting assumptions over stopping to ask |
| `python_style_001` | `has_docstrings` failed when agent used Write tool instead of code blocks | Check now falls back to written `.py` files when no code blocks found |

**Shared fix:** Added `require_language_tag` parameter to `_security_lib.py` and `detect_target_language()` helper. Check scripts now extract only explicitly tagged code blocks for the target language, preventing false positives from anti-pattern examples in prose and cross-language written file content.

### Results by skill category

| Category | Cases | Rubric Δ | Positive check flips |
|---|---|---|---|
| Efficiency (from-scratch) | 18 | +9 | 1 (tag filter TS) |
| Efficiency (extend-existing) | 9 | +14 | 2 (nested loop C, string concat Go) |
| Efficiency (review) | 9 | +3 | 0 |
| Efficiency (new rule coverage) | 16 | +2 | 0 |
| Security | 53 | +36 | 1 (headers) |
| SDLC | 3 | +10 | 1 (observability) |
| Dev workflow + orchestration | 3 | +9 | 2 (TDD, multi-skill) |
| CI/CD | 14 | +66 | 10 (all 7 languages) |
| SQL | 22 | +29 | 4 (pagination, MySQL schema, PG JSONB, MSSQL schema) |
| Package-specific | 21 | +39 | 0 (rubric-only, 7 timed out) |
| Python style + streaming | 2 | +5 | 0 |

### CI/CD results (14 cases across 7 languages)

**The highest-impact skill category.** Total CI/CD rubric: 66 → 132 (+66). Check flips: 10.

| Case | Baseline | With skill | Δ | Checks |
|---|---|---|---|---|
| `cicd_python` | 1 | 14 | **+13** | 0/3 → 3/3 |
| `cicd_go` | 1 | 10 | **+9** | 0/3 → 3/3 |
| `cicd_gotcha_rust_incremental` | 2 | 10 | **+8** | 2/3 → 3/3 |
| `cicd_csharp` | 4 | 10 | **+6** | 0/3 → 3/3 |
| `cicd_cpp` | 3 | 8 | **+5** | 0/3 → 3/3 |
| `cicd_javascript` | 5 | 10 | **+5** | 1/3 → 3/3 |
| `cicd_php` | 6 | 10 | +4 | 1/3 → 2/3 |
| `cicd_rust` | 3 | 7 | +4 | 1/3 → 2/3 |
| `cicd_gotcha_python_tox` | 6 | 10 | +4 | 2/3 → 3/3 |
| `cicd_gotcha_csharp_chain` | 6 | 10 | +4 | 2/3 → 3/3 |
| `cicd_gotcha_go_race` | 6 | 8 | +2 | 2/3 → 3/3 |
| `cicd_gotcha_php_pcov` | 8 | 10 | +2 | 3/3 → 3/3 |
| `cicd_gotcha_js_npm_ci` | 8 | 8 | 0 | 3/3 → 3/3 |

**Baseline lacks caching, coverage, and linting across all languages.** Without the skill, Sonnet generates minimal workflows that run tests but omit dependency caching, code coverage, and linting. The skill adds all three consistently.

**Gotcha cases show language-specific knowledge:** The skill teaches Rust `CARGO_INCREMENTAL=0` (+8), Python tox caching (+4), C# `--no-restore`/`--no-build` chaining (+4), Go `-race` flag (+2), and PHP `pcov` over xdebug (+2).

### Package-specific results (21 cases across 21 frameworks)

Total rubric (14 completed): 112 → 151 (+39). 11 improved, 3 flat, 7 timed out.

| Case | Baseline | With skill | Δ |
|---|---|---|---|
| `pkg_asp_net_di` | 3 | 11 | **+8** |
| `pkg_flask_factory` | 6 | 12 | **+6** |
| `pkg_fastapi_async` | 9 | 14 | **+5** |
| `pkg_celery_task_design` | 8 | 12 | **+4** |
| `pkg_maud_templates` | 9 | 12 | **+3** |
| `pkg_sqlx_queries` | 7 | 10 | **+3** |
| `pkg_starlette_websocket` | 5 | 8 | **+3** |
| `pkg_django_n_plus_one` | 4 | 6 | **+2** |
| `pkg_react_native_list` | 8 | 10 | **+2** |
| `pkg_sqlalchemy_eager_loading` | 8 | 10 | **+2** |
| `pkg_redis_caching` | 10 | 11 | **+1** |
| `pkg_nextjs_server_components` | 12 | 12 | 0 |
| `pkg_react_performance` | 11 | 11 | 0 |
| `pkg_vue_composables` | 12 | 12 | 0 |

**Biggest impact:** ASP.NET DI lifetimes/middleware (+8), Flask factory pattern (+6), FastAPI async/Depends (+5), Celery task design (+4). These are frameworks where the baseline produces working-but-naive code and the skill adds production patterns.

**Already strong baselines (Δ=0):** Next.js Server Components, React useMemo patterns, Vue 3 Composition API. Sonnet already knows modern frontend idioms.

**Previously failed (resolved):** Apalis (+7), MUI (0), RabbitMQ (+2), Tailwind (-1) — fixed by increasing timeout to 600s and piping scorer/differ prompts via stdin to avoid Windows command-line length limits. Axum, NestJS, ZeroMQ — intermittent claude CLI init errors, resolved with retry logic.

### SQL results (22 cases across 5 dialects)

Total SQL rubric: 173 → 202 (+29). 15 improved, 7 flat.

| Case | Baseline | With skill | Δ | Checks |
|---|---|---|---|---|
| `sql_pagination` | 2 | 7 | **+5** | 0/1 → 1/1 |
| `sql_mssql_cross_apply` | 4 | 8 | **+4** | 1/1 → 1/1 |
| `sql_mysql_schema` | 7 | 10 | **+3** | 2/2 → 2/2 |
| `sql_top_n_per_group` | 5 | 8 | **+3** | 1/1 → 1/1 |
| `sql_null_handling` | 8 | 10 | +2 | n/a |
| `sql_oracle_hierarchy` | 6 | 8 | +2 | n/a |
| `sql_pg_schema` | 8 | 10 | +2 | 1/2 → 1/2 |
| `sql_money_calc` | 9 | 10 | +1 | 1/1 → 1/1 |
| `sql_migration` | 9 | 10 | +1 | n/a |
| `sql_mssql_schema` | 9 | 10 | +1 | 1/2 → 2/2 |
| `sql_mssql_error_handling` | 9 | 10 | +1 | 1/1 → 0/1 |
| `sql_mysql_json` | 7 | 8 | +1 | 1/1 → 1/1 |
| `sql_mysql_upsert` | 5 | 6 | +1 | 0/1 → 1/1 |
| `sql_oracle_bulk` | 9 | 10 | +1 | n/a |
| `sql_oracle_schema` | 9 | 10 | +1 | 2/2 → 2/2 |

**Skill adds the most value for:** Keyset pagination over OFFSET (+5, check flip), CROSS APPLY over correlated subqueries (+4), MySQL schema best practices (+3, utf8mb4/BIGINT/InnoDB), window functions for top-N-per-group (+3). The skill also consistently improves dialect-specific patterns: Oracle PL/SQL bulk ops, PostgreSQL JSONB indexes, MSSQL temporal tables.

**Baseline already handles well:** Basic schema constraints (PKs, FKs, NOT NULL), parameterized queries, proper monetary types (DECIMAL not FLOAT). Sonnet knows these fundamentals across all dialects.

### Security results (53 cases across 9 languages)

Total security rubric: 295 → 331 (+36).

| Case | Baseline | With skill | Δ | Checks |
|---|---|---|---|---|
| `security_headers` | 1 | 10 | **+9** | 0/2 → 2/2 |
| `security_request_logger` | 1 | 6 | **+5** | 1/1 → 1/1 |
| `security_sql_injection_ts` | 3 | 6 | **+3** | 1/1 → 1/1 |
| `security_error_handling` | 7 | 10 | **+3** | 3/3 → 3/3 |
| `security_authorization` | 6 | 8 | +2 | 1/2 → 1/2 |
| `security_command_injection` | 4 | 6 | +2 | 1/1 → 1/1 |
| `security_path_traversal` | 6 | 8 | +2 | 1/1 → 1/1 |
| `security_sql_injection_js` | 4 | 6 | +2 | 1/1 → 1/1 |
| `security_csrf` | 7 | 8 | +1 | 2/2 → 2/2 |
| `security_sql_injection_cpp` | 4 | 5 | +1 | 1/1 → 1/1 |
| `security_ssrf` | 7 | 8 | +1 | 1/1 → 1/1 |
| `security_cookie_flags` | 10 | 10 | 0 | 2/2 → 2/2 |
| `security_deserialization` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_hardcoded_secret` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_input_validation` | 9 | 9 | 0 | 2/2 → 2/2 |
| `security_password_hash` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_rng_token` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_sql_injection` | 5 | 5 | 0 | 1/1 → 1/1 |
| `security_sql_injection_c` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_sql_injection_csharp` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_sql_injection_go` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_sql_injection_php` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_sql_injection_rust` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_tls_client` | 6 | 6 | 0 | 1/1 → 1/1 |
| `security_xss` | 8 | 8 | 0 | 2/2 → 2/2 |
| `security_xxe` | 8 | 8 | 0 | 1/1 → 1/1 |

**Cross-language coverage (27 cases across Go, JS, PHP, C#, Rust, C++):**

| Rule | Languages tested | All checks pass? | Rubric Δ |
|---|---|---|---|
| SQL injection | Go, JS, TS, PHP, C#, Rust, C, C++ | Yes (all 8) | +6 |
| Hardcoded secrets | Go, JS, PHP, C#, Rust, C++ | 5/6 (Go check regressed) | +4 |
| Password hashing | Go, JS, PHP, C# | Yes (all 4) | 0 |
| Insecure RNG | Go, JS, PHP, C# | Yes (all 4) | 0 |
| Path traversal | Go, JS, PHP | 2/3 (Go check regressed) | 0 |
| XSS | Go, JS, PHP | 2/3 (JS check fails both) | +2 |
| Deserialization | PHP, C# | Yes (both) | +1 |
| TLS disabled | Go, JS | 1/2 (JS check regressed) | 0 |
| Command injection | JS, PHP (Go failed) | 1/2 (PHP check fails both) | -2 |

**Baseline already handles well across all languages:** SQL injection, password hashing, insecure RNG, deserialization, TLS verification, path traversal, XSS. Modern Sonnet uses parameterized queries, bcrypt/argon2, crypto-secure RNG, and safe deserialization by default in every language tested.

**Skill adds value:** Security headers (+9, check flip), secret logging/redaction (+5), fail-closed error handling (+3), hardcoded secrets in PHP/C#/C++ (+4), XSS in JS (+2), IDOR authorization (+2), SSRF host validation (+1), CSRF protection (+1).

### Key takeaways

1. **CI/CD skills have the highest impact of any category** (+66 across 14 cases, 10 check flips). Sonnet generates minimal workflows without the skill; with it, every language gets dependency caching, code coverage, and linting. SDLC practices (observability +9, API design +4, TDD +3) and extend-existing-code tasks (+14 across 9 cases) are also strong. These are tasks where the baseline produces functional-but-incomplete output and the skill adds production-readiness.

2. **Security skills have the most impact on infrastructure-level concerns.** Modern Sonnet already handles common vulnerabilities (SQL injection, XSS, path traversal, XXE, input validation, cookie flags) without prompting. The skill adds the most value for security headers (+9), secret logging (+5), error handling (+3), and SSRF/authorization (+2 each) — areas where the baseline produces working code but omits hardening.

3. **The "extend inefficient code" paradigm is the best discriminator** for efficiency skills. Giving the agent existing inefficient code and asking it to build on it reveals whether the skill overrides the "copy the existing pattern" impulse. The Go `string +=` and C nested-loop cases flip reliably.

4. **Multi-skill orchestration requires the `skill-orchestration` meta-skill.** Without it, the agent invokes only one skill even when multiple are relevant. With it, all relevant skills are invoked and their guidance composes.

5. **Check scripts must be language-aware.** Three initial negative check flips traced to Python-centric regex being applied to Go/JS/PHP output. Fixed by adding `detect_target_language()` and `require_language_tag` to the shared helper, so each check extracts only the target language's code blocks and applies language-appropriate patterns.
