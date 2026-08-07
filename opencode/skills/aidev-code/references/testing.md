# Testing Conventions

This file establishes universal testing principles for all code. These conventions are distilled from the organization's testing standards across all supported stacks.

**MCP discovery**: the specific testing framework, assertion library, mocking library, mutation testing tool, and formatting tool for the detected stack must be discovered at runtime by querying available MCP documentation tools. Search for the stack's testing setup, conventions, and commands via MCP before writing any tests.

## Technical-Check Execution Policy

This is the authoritative policy for selecting and scheduling technical checks: tests, builds, linters, type checks, and formatters.

- **Code batch** — a coherent set of related implementation units in one repository that advances one planned behavior or dependency-ordered slice. It ends when that slice is implemented, a dependency boundary is reached, or the repository is ready for independent validation.
- **Test batch** — the test files and cases that cover the code batch's new or changed behavior. Write these tests while implementing the batch; “batch tests” means batch their _execution_, not postpone their authoring until all code is complete.
- **Batch boundary** — the point after the code and test batch is complete and before independent validation. Apply the formatter once here.
- **Implement in batches** — write production code and its tests together, then continue through a coherent repository batch. Do not automatically run a technical command because an individual unit or task has ended.
- **Use the repository command surface** — when a repository-root Taskfile exists, use its matching `task <name>` command for every technical check. Otherwise, use the repository's documented command. Before the first package-based check, run the Taskfile's `install` task when available. Version checks and one-off diagnostics are exempt.
- **Prepare once at the batch boundary** — before independent validation, run the stack formatter once in write mode when applicable.
- **Use targeted checks only by exception** — run a scoped test or other technical check during implementation only to investigate a known failure, when explicitly required by the task, or at an identified high-risk boundary. Do not use a partial check merely because a unit of work finished.
- **Reuse passing evidence** — record commands, scope, inputs, and results. Do not rerun a passing check unless a relevant file or configuration change invalidates its evidence.

## Test Naming

- **Use descriptive, action-result naming** — test names must clearly express what action is being tested and what result is expected. Follow the pattern: `{action}_{expected_result}` or an equivalent convention for the stack.
- **Be specific about the scenario** — test names should describe the specific condition or input, not just the method being tested. A reader should understand what the test validates without reading the body.
- **Follow the stack's naming convention** — each stack has its own naming style (snake_case, PascalCase, camelCase). Discover the correct convention via MCP.
- **Do not include the word "test" redundantly** — the test framework already identifies tests. Avoid tautological naming.

## 3A / AAA Pattern

Structure every test as Arrange, Act, Assert — three distinct phases in every test method:

1. **Arrange**: set up preconditions, create test data, configure mocks.
2. **Act**: execute the single operation under test.
3. **Assert**: verify the expected outcome.

Rules:

- **Separate sections visually** — use blank lines between the three sections. Follow the stack's convention on whether section comments are appropriate (discover via MCP).
- **One act per test** — each test exercises exactly one behavior. Multiple assertions about the same result are fine. Different behaviors require separate tests.
- **Keep arrange minimal** — if the arrange section is large, extract it into a test data builder or fixture (see Object Mother section).

## Coverage Thresholds

- **Minimum 80% line coverage** — every module/package must achieve at least 80% line coverage.
- **Minimum 80% branch coverage** — at least 80% of conditional branches must be exercised by tests.
- **Minimum 80% mutation coverage** — at least 80% of code mutations must be detected (killed) by the test suite. Discover the stack's mutation testing tool via MCP.
- **Coverage is a floor, not a ceiling** — 80% is the minimum. Critical business logic (payment processing, authorization decisions, data integrity checks) should aim for higher coverage.
- **Coverage reports integrate with corporate quality tooling** — the organization provides quality dashboards. Discover the specific integration via MCP.

## Mocking Patterns

- **Mock only at external boundaries** — mock external dependencies (database, HTTP clients, message queues, file systems, third-party services). Do not mock the class under test or its internal collaborators.
- **Prefer constructor injection for testability** — design production code so dependencies are injected via constructors. This enables easy substitution with mocks in tests without reflection or framework magic.
- **Verify mock interactions sparingly** — verify that a mock was called only when the call itself is the behavior under test (e.g., "this operation must send a notification"). Do not verify every mock call — that creates brittle tests coupled to implementation details.
- **Use argument capture when assertion requires it** — when you need to inspect the actual arguments passed to a dependency, use the stack's argument capture mechanism rather than matching on exact values.
- **Reset mocks between tests** — ensure test isolation by resetting mock state. Each test must be independent of mock state from other tests.

## Object Mother / Test Data Builders

- **Use the Object Mother or test builder pattern** — create dedicated factory functions/classes that produce valid test objects with sensible defaults. Tests override only the fields relevant to their scenario.
- **Centralize test data creation** — do not duplicate object construction across test files. Shared test data builders live in a common test utilities location.
- **Defaults must produce valid objects** — the base builder/mother must return an object that passes all validation rules. Tests then customize specific fields to test edge cases.
- **Name builders descriptively** — builder methods should read naturally: `aValidUser()`, `anExpiredToken()`, `createTestOrder(status=...)`.

## Deterministic Time Handling

- **Never use "now" in tests** — do not call the system clock in test code. Tests that depend on the current time are non-deterministic and will eventually fail.
- **Use fixed time values** — define explicit, constant time values for all test scenarios. Choose values that are clearly test data (not close to epoch or current date).
- **Inject time as a dependency in production code** — design production code to accept a clock/time source as a dependency so tests can provide a fixed time. Discover the stack's clock injection pattern via MCP.

## Parameterized / Table-Driven Tests

- **Use parameterized tests for multiple scenarios** — when the same behavior needs to be tested with different inputs, use the stack's parameterized/table-driven test mechanism instead of duplicating test methods.
- **Give each test case a descriptive name** — parameterized test cases must have human-readable names that appear in test output. Use the naming/ID mechanism provided by the test framework.
- **Keep the test logic identical across cases** — if different cases require different assertions or setup, they should be separate tests, not parameterized.

## Evidence and Failure Handling

- **Record the check scope** — evidence must state `scope: complete` or `scope: targeted`, the command, covered change/checks, result, and any prior evidence reused.
- **Fix failed checks before progressing to the next batch** — return through the focused implementation and validation loop. Do not stack unrelated batches on a red baseline.
- **Never weaken tests to go green** — do not skip, delete, or loosen existing tests to make a check pass; a legitimately failing existing test is a finding to report, not noise to silence.
- **Formatting is mandatory** — format both production and test code during batch preparation. A format-check failure returns to implementation for correction.
