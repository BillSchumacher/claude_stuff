---
name: dev-workflow
description: Use when implementing any feature, bugfix, or refactor that involves writing code. Enforces TDD with Gherkin scenarios (Given/When/Then), code quality verification, and disciplined git workflow.
---

## Planning & Execution

- Before writing code, read the relevant files and understand existing patterns.
- Break work into small, verifiable steps. Complete and verify each step before moving to the next.
- Check assumptions against the actual codebase — don't guess at function signatures, file paths, or data shapes.
- When modifying existing code, verify that callers and dependents still work after changes.

## Test-Driven Development

Follow this exact TDD cycle for every feature:

1. **Write test file first.** Create a test file with all test functions before writing any implementation code. Every test function MUST have a docstring in Gherkin format using "Given", "When", "Then":
   ```python
   def test_pop_returns_top():
       """
       Given a stack with items [1, 2, 3]
       When I pop from the stack
       Then the result is 3
       And the stack contains [1, 2]
       """
   ```
2. **Run the tests.** Execute the test suite and confirm the tests fail (since no implementation exists yet). This verifies the tests are actually testing something.
3. **Write the implementation.** Now write the minimal code to make the tests pass.
4. **Run the tests again.** Confirm all tests pass with the implementation.

Never skip step 2. Seeing the tests fail first is essential — it proves they are valid tests that exercise the code.

When fixing a bug, write a failing test that reproduces it before applying the fix.

## Code Quality

- Read a file before editing it. Never modify code you haven't seen.
- Run tests after every change — don't batch multiple changes before verifying.
- Run the project's linter before considering work complete.
- Verify that new code doesn't break existing functionality by checking test results and reviewing affected call sites.

## Git Workflow

- Make focused commits that each represent a single logical change.
- Write commit messages that explain why, not just what.
- Never force-push, amend published commits, or reset shared branches without explicit confirmation.
- Stage specific files rather than using `git add .` or `git add -A`.
- Review the diff before committing to catch unintended changes.
