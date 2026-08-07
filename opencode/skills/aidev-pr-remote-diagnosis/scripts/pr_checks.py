#!/usr/bin/env python3
"""pr_checks.py — deterministic remote PR check inspection.

Bundled tool of the `aidev-pr-remote-diagnosis` skill. It is the cheap,
deterministic pre-check that runs BEFORE the interpretive skill body: a caller
runs it against a pushed PR head commit and only loads the LLM diagnosis when a
check is actually red, pending, or ambiguous. `AIDevVerifier` uses it in its
`in_review_wait` PR delivery path (report-only, after a draft PR is marked ready
for review); `AIDevCoder` never inspects remote checks — it leaves every PR in
DRAFT.

It inspects the remote status of a pushed PR head commit using the `gh` CLI and
returns a machine-readable verdict so the caller can short-circuit when the PR
is already clean.

Scope (deterministic only — see the skill body for the interpretive rest):
  - Inspect the PR head commit's status check rollup (check runs + status contexts).
  - Compute a conservative global status (passed | failed | pending).
  - Map KNOWN check names to agnostic categories (ci, coverage, convention, ...).
  - Parse KNOWN provider payloads with stable formats: SonarCloud quality-gate
    comment metrics (coverage / duplication / new issues / gate) and the Sherpa
    branch-vs-body closing-keyword delta.

Explicitly NOT in scope (requires flexible interpretation → keep in the LLM skill):
  - Interpreting arbitrary CI job logs (failing command, file/line, root cause).
  - Classifying unknown checks or reconciling contradictory evidence.
  - Synthesising a fix plan (which tests to add, which code to touch, safe_to_apply).

Usage:
  pr_checks.py --repo <owner/repo> --pr <number> [--head <sha>]

Output: a single JSON object on stdout.

Exit codes (cheap gate for the caller):
  0  passed   — every check for the head commit is green / neutral / skipped.
  1  failed   — at least one check failed / errored / was cancelled.
  2  pending  — no failures, but at least one check is still queued or running
                (or the head has no checks yet).
  3  error    — the inspection itself could not run (gh missing/unauth, PR not
                found, malformed output). Treat as "not clean": fall back to the
                aidev-pr-remote-diagnosis skill.
"""
import argparse
import json
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Known-check → agnostic category lookup. Matching is substring/regex, case
# insensitive, so provider suffixes and org prefixes still resolve. Unknown
# checks intentionally map to None so the caller routes them to the LLM skill.
# ---------------------------------------------------------------------------
CATEGORY_PATTERNS = [
    ("coverage", r"sonar|coverage|quality gate"),
    ("convention", r"sherpa|convention|semantic|commitlint|danger"),
    ("security", r"security|snyk|secret|trivy|codeql|dependency"),
    ("ci", r"verify|build|test|lint|typecheck|package|deploy|ci\b|pipeline|actions"),
]

# gh statusCheckRollup conclusions/states that are terminal-green, terminal-red,
# or still non-conclusive. Anything unrecognised is treated as pending (safe).
GREEN = {"SUCCESS", "NEUTRAL", "SKIPPED"}
RED = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
PENDING = {"PENDING", "QUEUED", "IN_PROGRESS", "EXPECTED", "WAITING", "REQUESTED", "STALE", ""}


def gh_json(args):
    """Run a `gh` command and parse its JSON stdout. Raises on any failure."""
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh {' '.join(args)} returned non-JSON output: {exc}")


def categorize(name):
    low = (name or "").lower()
    for category, pattern in CATEGORY_PATTERNS:
        if re.search(pattern, low):
            return category
    return None


def normalize_check(item):
    """Flatten a statusCheckRollup node (CheckRun or StatusContext) to a common shape."""
    typename = item.get("__typename", "")
    if typename == "StatusContext":
        name = item.get("context") or "unknown"
        state = (item.get("state") or "").upper()
        conclusion = state
        status = "COMPLETED" if state in GREEN | RED else state
        url = item.get("targetUrl")
    else:  # CheckRun (default)
        name = item.get("name") or "unknown"
        status = (item.get("status") or "").upper()
        conclusion = (item.get("conclusion") or "").upper()
        url = item.get("detailsUrl")

    if conclusion in RED:
        verdict = "failed"
    elif status in ("COMPLETED", "SUCCESS") and (conclusion in GREEN or (not conclusion and status == "SUCCESS")):
        verdict = "passed"
    elif conclusion in GREEN:
        verdict = "passed"
    else:
        verdict = "pending"

    return {
        "name": name,
        "status": status or None,
        "conclusion": conclusion or None,
        "verdict": verdict,
        "category": categorize(name),
        "url": url,
        # rollup is always scoped to the current head commit
        "head_match": True,
    }


def compute_status(checks):
    if any(c["verdict"] == "failed" for c in checks):
        return "failed"
    if any(c["verdict"] == "pending" for c in checks):
        return "pending"
    if not checks:
        # No checks reported yet for this head — not proven clean.
        return "pending"
    return "passed"


# ---------------------------------------------------------------------------
# Known provider parsers (stable formats only). Best-effort: any field that
# cannot be found stays null instead of raising, so a format drift degrades
# gracefully to "let the LLM skill look at it".
# ---------------------------------------------------------------------------
def parse_sonar(comments):
    sonar_comments = [
        c for c in comments
        if "sonarqubecloud" in (c.get("author", {}).get("login", "").lower())
        or "sonarcloud" in (c.get("body", "").lower()[:200])
    ]
    if not sonar_comments:
        return {"present": False}
    latest = sonar_comments[-1]
    body = latest.get("body", "")

    def num(pattern):
        m = re.search(pattern, body, re.IGNORECASE)
        return float(m.group(1)) if m else None

    gate = None
    if re.search(r"quality gate\s*(passed|✅)", body, re.IGNORECASE):
        gate = "passed"
    elif re.search(r"quality gate\s*(failed|❌)", body, re.IGNORECASE):
        gate = "failed"

    return {
        "present": True,
        "quality_gate": gate,
        "coverage": num(r"([\d.]+)%\s*Coverage"),
        "duplication": num(r"([\d.]+)%\s*Duplicat"),
        "new_issues": int(num(r"(\d+)\s+New issues") or 0) if re.search(r"New issues", body, re.IGNORECASE) else None,
        "comment_url": latest.get("url"),
        # The comment does not reliably carry the analysed SHA in a stable field.
        "head_match": "unknown",
    }


def parse_sherpa(branch, body):
    """Compare the branch's issue key against the PR body's closing keyword."""
    branch_issue = None
    m = re.search(r"(?:^|[/_-])(?:gh|issue)?-?(\d{1,6})(?:[/_-]|$)", branch or "", re.IGNORECASE)
    if m:
        branch_issue = m.group(1)

    body_closes = None
    m = re.search(r"\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\b[^\d#]*#(\d{1,6})",
                  body or "", re.IGNORECASE)
    if m:
        body_closes = m.group(1)

    if branch_issue is None and body_closes is None:
        return {"present": False}
    return {
        "present": True,
        "branch_issue": branch_issue,
        "body_closes_issue": body_closes,
        "match": bool(branch_issue) and branch_issue == body_closes,
    }


def build_report(repo, pr):
    pr_data = gh_json([
        "pr", "view", str(pr), "-R", repo,
        "--json", "number,headRefOid,headRefName,url,statusCheckRollup,comments,body",
    ])
    head = pr_data.get("headRefOid")
    rollup = pr_data.get("statusCheckRollup") or []
    checks = [normalize_check(item) for item in rollup]
    status = compute_status(checks)

    counts = {"passed": 0, "failed": 0, "pending": 0}
    for c in checks:
        counts[c["verdict"]] += 1

    sonar = parse_sonar(pr_data.get("comments") or [])
    sherpa = parse_sherpa(pr_data.get("headRefName", ""), pr_data.get("body", ""))

    return {
        "repo": repo,
        "pr": pr_data.get("number", pr),
        "url": pr_data.get("url"),
        "head": head,
        "branch": pr_data.get("headRefName"),
        "status": status,
        "counts": counts,
        "checks": checks,
        "sonar": sonar,
        "sherpa": sherpa,
        # The caller only needs to spend the interpretive skill when not clean.
        "needs_llm_diagnosis": status != "passed",
        "reason": {
            "passed": "every check for the head commit is green/neutral/skipped",
            "failed": "at least one check failed for the head commit",
            "pending": "no failures, but at least one check is not conclusive yet",
        }[status],
    }


STATUS_EXIT = {"passed": 0, "failed": 1, "pending": 2}


def main(argv):
    parser = argparse.ArgumentParser(description="Deterministic remote PR check inspection.")
    parser.add_argument("--repo", required=True, help="GitHub repository as owner/repo")
    parser.add_argument("--pr", required=True, help="PR number")
    parser.add_argument("--head", help="Expected head commit SHA (advisory; flagged when it drifts)")
    args = parser.parse_args(argv)

    try:
        report = build_report(args.repo, args.pr)
    except Exception as exc:  # noqa: BLE001 — any failure means "not proven clean"
        print(json.dumps({
            "repo": args.repo,
            "pr": args.pr,
            "status": "error",
            "needs_llm_diagnosis": True,
            "error": str(exc),
            "reason": "inspection could not run; fall back to aidev-pr-remote-diagnosis",
        }, indent=2))
        return 3

    if args.head and report.get("head") and args.head != report["head"]:
        report["head_drift"] = {"expected": args.head, "actual": report["head"]}
        report["needs_llm_diagnosis"] = True

    print(json.dumps(report, indent=2))
    return STATUS_EXIT.get(report["status"], 3)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
