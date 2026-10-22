# Project-Specific Development Standard

Instructions for this project. Anything here overwrites global rules.

- Use skills proactively when they match the task — suggest relevant ones, don't block on them

## Philosophy
- **Tests drive code** - We will employ Red/Green Test-Driven Development at every step. Only write code that is required to make a test pass.
- **No speculative features** - Don't add features, flags, or configuration unless users actively need them
- **No premature abstraction** - Don't create utilities until you've written the same code three times
- **Clarity over cleverness** - Prefer explicit, readable code over dense one-liners
- **Justify new dependencies** - Each dependency is attack surface and maintenance burden
- **No phantom features** - Don't document or validate features that aren't implemented
- **Replace, don't deprecate** - When a new implementation replaces an old one, remove the old one entirely. No backward-compatible shims, dual config formats, or migration paths. Proactively flag dead code — it adds maintenance burden and misleads both developers and LLMs.
- **Verify at every level** - Set up automated guardrails (linters, type checkers, pre-commit hooks, tests) as the first step, not an afterthought. Prefer structure-aware tools (ast-grep, LSPs, compilers) over text pattern matching. Review your own output critically. Every layer catches what the others miss.
- **Bias toward action** - Decide and move for anything easily reversed; state your assumption so the reasoning is visible. Ask before committing to interfaces, data models, architecture, or destructive/write operations on external services.
- **Finish the job** - Don't stop at the minimum that technically satisfies the request. Handle the edge cases you can see — by writing tests for them first, then making those tests pass. Clean up what you touched. If something is broken adjacent to your change, flag it. But don't invent new scope — there's a difference between thoroughness and gold-plating. Never implement an untested edge case.
- **Agent-native by default** - Design so agents can achieve any outcome users can. Tools are atomic primitives; features are outcomes described in prompts. Prefer file-based state for transparency and portability. When adding UI capability, ask: can an agent achieve this outcome too?

## Code Quality

### Hard limits

1. ≤100 lines/function, cyclomatic complexity ≤8
2. ≤5 positional params
3. 100-char line length
4. No parent-directory traversal in imports (`..`). Same-package relative imports (`from . import x`) are acceptable.
5. Google-style docstrings on non-trivial public APIs

### Zero warnings policy

Fix every warning from every tool — linters, type checkers, compilers, tests. If a warning truly can't be fixed, add an inline ignore with a justification comment. Never leave warnings unaddressed; a clean output is the baseline, not the goal.

### Comments

- Code should be as self-documenting as possible. No commented-out code—delete it. If you need a comment to explain WHAT the code does, refactor the code instead.
- Add a comment documenting why a function exists when the reason is non-obvious from its name and signature.

### Error handling

- Fail fast with clear, actionable messages
- Never swallow exceptions silently
- Include context (what operation, what input, suggested fix)

### Reviewing code

Evaluate in order: architecture → code quality → tests → performance. Before reviewing, sync to latest remote (`git fetch origin`).

For each issue: describe concretely with file:line references, present options with tradeoffs when the fix isn't obvious, recommend one, and ask before proceeding.

### Testing

**Tests are written before implementation.** See the TDD cycle in the Workflow section. The test suite is the primary specification of what the system does.

**Test file organization mirrors source structure.** Tests live in a `tests/` directory. One test file per source module (e.g., `tests/test_parser.py` covers `src/parser.py`). Reading the test file should tell you everything the module does.

**Test names should describe the intended behavior of the behavior under test.** Use the following naming convention:
	  test_<subject>_<condition>_<expected_result>
		# e.g. test\_parser\_empty\_input\_raises\_value\_error

**Test behavior, not implementation.** Tests should verify what code does, not how. If a refactor breaks your tests but not your code, the tests were wrong.

**Test edges and errors, not just the happy path.** Empty inputs, boundaries, malformed data, missing files, network failures — bugs live in edges. Every error path the code handles should have a test that triggers it.

**Mock boundaries, not logic.** Only mock things that are slow (network, filesystem), non-deterministic (time, randomness), or external services you don't control.

## Development

When adding dependencies, CI actions, or tool versions, always look up the current stable version — never assume from memory unless the user provides one.


## Workflow

**TDD cycle**
0. Run the full test suite. All existing tests must pass before you add anything new — start from green.
1. Write a test for the next behavior to add.
2. Run the new test and confirm it fails. Check that it fails for the expected reason (the right assertion fires, not a syntax error or import failure).
3. Write just enough code to make the new test pass, but no more.
4. Refactor the code to conform to code quality standards.
5. Rerun the new test and confirm it still passes.
6. Run the full test suite and confirm no existing tests regressed.

If at any point this process breaks down, review the test and ensure it accurately and adequately tests for the desired behavior.
If the test does not meet this standard, discard it and start from step 1.
If the test does meet this standard, discard the code changes and return to step 3.

**Before committing:**
1. Re-read your changes for unnecessary complexity, redundant code, and unclear naming
2. Run the full test suite and verify that there are no failures.
3. Run linters and type checker — fix everything before committing

**Commits:**
- Imperative mood, ≤72 char subject line, one logical change per commit
- Never amend/rebase commits already pushed to shared branches
- Never push directly to main — use feature branches and PRs
- Never commit secrets, API keys, or credentials — use `.env` files (gitignored) and environment variables

**Pull requests:**
Describe what the code does now — not discarded approaches, prior iterations, or alternatives. Only describe what's in the diff.

Use plain, factual language. A bug fix is a bug fix, not a "critical stability improvement." Avoid: critical, crucial, essential, significant, comprehensive, robust, elegant.
