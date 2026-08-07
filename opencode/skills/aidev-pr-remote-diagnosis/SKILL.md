---
name: aidev-pr-remote-diagnosis
description: Inspect pushed GitHub pull request remote checks and produce an agnostic diagnosis plus fix plan. Use after commits are pushed to a PR, especially when GitHub Actions, SonarCloud, Sherpa conventions, Code / Verify, or other remote-only PR checks fail or remain pending.
---

# AIDev PR Remote Diagnosis

Use this skill after a branch has been pushed and a pull request exists. Its job is to interpret what is actually failing on a PR and return a concrete fix plan. It is diagnosis and fix-plan only: it may recommend safe PR metadata edits, but the caller applies fixes, commits, pushes, and re-checks. It does not declare implementation complete, commit fixes, push branches, or perform destructive issue/branch/PR topology changes.

## Inputs

The caller provides:

- `repo`: GitHub repository as `owner/repo`.
- `pr`: PR number or URL.
- `branch`: PR head branch when known.
- `commit`: pushed head commit SHA when known, or `unknown`.
- `journal`: path to the implementation journal when available.
- `attempt`: remote diagnosis/fix attempt number for this PR.
- `pr_checks_json`: the output of a deterministic pre-check when the caller ran one (global status, per-check verdict/category, and any parsed SonarCloud/Sherpa payloads). Absent when no pre-check ran or it could not complete.

## Required Sources

When `pr_checks_json` is provided, the deterministic inspection — check runs, global status, known-check categorisation, and stable-format provider metrics — is already done and delivered there. Fetch raw evidence yourself only for the checks it flagged (primarily failed job logs), or for every source below when `pr_checks_json` is unavailable. Inspect in this priority order:

1. `github-remote_pull_request_read(method=get_check_runs)` for the PR head commit.
2. `github-remote_pull_request_read(method=get_comments)` for bot comments and reviewer automation comments.
3. `github-remote_get_job_logs` for failed GitHub Actions jobs when logs are available.
4. `github-remote_pull_request_read(method=get)` for branch, title, body, and linked metadata.

Use `gh` CLI equivalents only when the runtime does not expose the `github-remote_*` tools. Record which source produced each finding.

## Status Semantics

Return one overall status:

| Status    | Meaning                                                                                                                                     |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `passed`  | All required remote checks visible for the PR head commit are passing or neutral/skipped in a way that does not block merge.                |
| `failed`  | At least one required remote check failed and there is enough evidence to plan a concrete fix.                                              |
| `pending` | Required checks are queued, in progress, missing from the latest commit, or not yet conclusive.                                             |
| `blocked` | Diagnosis cannot continue without user input, credentials, unavailable logs, ambiguous topology, or a destructive/topology-changing action. |

Do not return `passed` if any required check is red, still running, stale for an older commit, or contradicted by a newer bot comment.

## Classification

Classify each failing or blocking finding into one of these agnostic categories:

| Category          | Detect                                                                                                                                               | Fix plan guidance                                                                                                                                                                   |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `coverage`        | Coverage gate below threshold, commonly from SonarCloud comments or check details.                                                                   | Plan a targeted test-coverage fix pass. Prefer adding or updating tests for uncovered new behavior. Do not lower thresholds or exclude production files unless explicitly approved. |
| `duplication`     | Duplicate-lines/new-code duplication quality gate.                                                                                                   | Plan a minimal refactor or test de-duplication that preserves behavior.                                                                                                             |
| `static-analysis` | Lint, typecheck, Sonar new issues, code smell, maintainability, or quality-gate issue failures.                                                      | Fetch details/logs, identify the concrete rule and file/line, run the matching local command if possible, and fix the issue.                                                        |
| `security`        | Vulnerability, security hotspot, secret scan, dependency alert, or security quality gate.                                                            | Fix the concrete issue. If resolution requires risk acceptance or weakening security controls, block for user approval.                                                             |
| `ci`              | GitHub Actions job failure such as `Code / Verify`, build, test, package, or deploy verify.                                                          | Fetch failed job logs, classify the failing command, reproduce locally when possible, and plan the smallest fix.                                                                    |
| `convention`      | PR title/body/branch naming/linking convention checks, including Sherpa.                                                                             | Prefer safe PR metadata fixes first: body, title, labels, or closing keyword format. Do not replace branches, PRs, or issues without explicit approval.                             |
| `topology`        | The only apparent fix is replacing/duplicating/closing/reopening an issue, branch, or PR, changing the linked issue, or rewriting published history. | Return `blocked` and ask for explicit user approval through the caller's native question mechanism.                                                                                 |
| `unknown`         | Evidence is insufficient or contradictory.                                                                                                           | Return `blocked` or `pending` with the missing evidence and the exact next diagnostic step.                                                                                         |

## Known Provider Parsers

When a deterministic pre-check ran, the SonarCloud metric extraction and the Sherpa branch/body delta below arrive pre-parsed in `pr_checks_json` (`sonar` and `sherpa` objects). Read those values instead of re-parsing the comment; use the recipes here only to reason about the fix, or to recover the data when `pr_checks_json` is unavailable. The **GitHub Actions / Code Verify Logs** parser stays interpretive — reading arbitrary job logs is not scriptable and is the main reason this skill is loaded.

### SonarCloud PR Comment Parsing

When a check named `SonarCloud Code Analysis` fails, or comments include `sonarqubecloud[bot]`:

1. Read PR comments and find the latest `sonarqubecloud[bot]` comment relevant to the current head commit.
2. Extract failed quality gate conditions, including:
   - New Code coverage percentage.
   - Required coverage threshold.
   - Duplication percentage or duplicated blocks.
   - New issues count and severity/rule when present.
   - Security hotspot or vulnerability status.
3. Distinguish the failure type:
   - Quality Gate failed due to coverage.
   - Quality Gate failed due to duplication.
   - Quality Gate failed due to new issues.
   - Security hotspot or vulnerability failure.
4. For coverage, inspect changed files and plan tests for uncovered new behavior. Do not recommend lowering thresholds. Do not recommend excluding production files unless the caller has explicit user approval.

### GitHub Actions / Code Verify Logs

When a check named `Code / Verify`, a GitHub Actions workflow, or a job conclusion is `failure`:

1. Fetch failed job logs when available.
2. Identify the failing command, package/module, file/line, and first actionable error.
3. Classify the failure by command behavior: build, lint, test, typecheck, package, deploy verify, or unknown.
4. Recommend running the matching local command when feasible before applying a fix.

### Sherpa Convention Checks

When a check named `sherpa-conventions` fails, or a message mentions branch naming, issue links, Jira key, closing keywords, default keywords, or linked issue mismatch:

1. Read the PR branch, title, and body.
2. Compare the branch issue key or number with the PR body closing keyword and linked issue metadata.
3. Prefer non-destructive metadata fixes first:
   - If the technical issue is in the same repository as the PR, prefer the short closing keyword form `Closes #<issue_number>`.
   - If the PR body says `Related to #<issue_number>` for the technical issue, recommend replacing it with `Closes #<issue_number>`.
   - If the technical issue is in a different repository than the PR, recommend the fully-qualified form `Closes owner/repo#<issue_number>`.
   - Never recommend closing keywords for parent backlog/user-story issues; those must remain sub-issue links or non-closing references.
   - Recommend PR title/body edits before branch or issue replacement.
4. Never recommend closing, reopening, duplicating, deleting, replacing, or relinking GitHub issues, branches, or PRs as an automatic fix. If that is required, return `blocked` with category `topology`.

## Safety Rules

- Do not close, reopen, duplicate, delete, replace, or relink GitHub issues, branches, or PRs to satisfy a remote check unless the user explicitly approves that exact artifact change through the caller's native question mechanism.
- Do not force-push, rewrite published history, change the base branch, or replace the PR without explicit approval.
- Do not lower quality gates, coverage thresholds, lint severity, security rules, or exclude production files unless explicitly approved.
- Prefer concrete, local, reversible fixes: tests, code fixes, configuration corrections, PR body/title edits, or rerunning a failed remote check when supported.

## Return Contract

End with exactly one YAML block matching this shape:

```yaml
remote_pr_diagnosis:
  repo: "owner/repo"
  pr: "https://github.com/owner/repo/pull/55"
  branch: "feature/GH-55-example"
  commit: "abc1234"
  attempt: 1
  status: "passed | failed | pending | blocked"
  summary: "One-sentence remote PR status summary."
  sources_checked:
    - "get_check_runs"
    - "get_comments"
    - "get_job_logs"
    - "get"
  findings:
    - check: "SonarCloud Code Analysis"
      status: "failed | passed | pending | blocked"
      category: "coverage | duplication | static-analysis | security | ci | convention | topology | unknown"
      evidence: "New Code coverage 78.3%, required 80%."
      source: "check_runs | comments | job_logs | pr_metadata"
      current_value: "78.3%"
      required_value: "80%"
  fix_plan:
    safe_to_apply: true
    requires_user_input: false
    summary: "Add focused tests for uncovered dashboard priority behavior."
    steps:
      - "Inspect changed files and coverage gap."
      - "Add or update tests only."
      - "Run local validation."
      - "Commit and push a follow-up fix."
  user_input:
    needed: false
    reason: null
    question: null
  journal_row:
    check: "SonarCloud Code Analysis"
    status: "failed"
    finding: "New Code coverage 78.3%, required 80%."
    action: "Add targeted tests."
    follow_up_commit: "pending"
```

If multiple checks fail, include one finding per check. The `journal_row` should summarize the highest-priority finding; the caller maps it into whatever remote-check journal rows or summary its own artifact defines.
