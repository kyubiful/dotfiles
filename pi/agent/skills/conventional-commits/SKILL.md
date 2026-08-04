---
name: conventional-commits
description: Create, prepare, validate, or review safe Git commits and commit messages using Conventional Commits 1.0.0. Use this skill whenever the user asks to commit, stage, propose, validate, or review repository changes or a commit message, mentions Conventional Commits, or wants to turn working-tree changes into a commit—even if they do not name the convention. Inspect the diff, propose an accurate type, scope, and breaking-change footer when appropriate; never add assistant co-authorship; and require `ask_user_question` approval immediately before `git commit`.
compatibility: Requires Git, shell access, and an ask_user_question-style interactive confirmation tool.
---

# Conventional Commits

Create a commit that accurately describes the change, works well with automation, and keeps the user in control. A commit changes shared history: do not execute it until the user has seen and approved the proposal in an interactive question.

## Format

Use these self-contained Conventional Commits 1.0.0 rules:

```text
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

- `type` is required and is followed by `:`; use a lowercase noun. Prefer `feat` for a new feature and `fix` for a bug fix.
- `scope` is optional and appears in parentheses: `feat(api): add pagination`.
- Place `!` before `:` when the change is breaking: `feat!: drop Node 18 support`.
- For a breaking change, also add a `BREAKING CHANGE: <explanation>` (or `BREAKING-CHANGE:`) footer.
- The body and footers are optional. Separate them from the summary with a blank line. Footers use `token: value` or `token #value`.
- Keep the summary imperative, concise, and specific. Do not invent a type or scope the diff does not support.

Common types, when appropriate: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `perf`, `style`, `chore`, and `revert`. The specification permits other types, but follow an existing repository convention where one exists.

## Workflow

1. **Understand the context.** Read `git status --short`, relevant changes (`git diff` and/or `git diff --cached`), and repository conventions: `CONTRIBUTING`, `README`, commit guidance, commitlint configuration, and a few recent commits. Do not include secrets, generated artifacts, or changes outside the request.
2. **Decide what belongs in the commit.**
   - If changes are staged, treat them as commit candidates and explain what they contain.
   - If changes are unstaged, do not run `git add .` or `git add -A` by default. Propose specific files and ask the user which to include when the selection is unclear.
   - If there are no changes, say so. Do not create an empty commit unless the user explicitly requests one.
3. **Propose the message.** Tie every part of the message to the diff. If the user supplied a message, validate its format and accuracy; suggest a correction when needed.
4. **Request final approval with `ask_user_question`.** Ask this question *after* staging exactly the agreed files and *immediately before* `git commit`. Show:
   - staged files and a short summary of their changes;
   - the complete proposed message, including body and footers;
   - one concise statement that no `Co-authored-by` trailer will be added.

   Mention this safeguard in the final approval and final report only; do not repeat it in every status update or message proposal.

   Offer these clear options:
   - **Create commit**: run the proposed command.
   - **Edit message**: collect or accept a revised message, then show final approval again.
   - **Cancel**: make no further index or history changes.

   Do not treat ambiguous text as approval. If an interactive tool is unavailable, show the proposal and request explicit natural-language confirmation; do not commit until it is received.
5. **Create the approved commit.** Write the approved message to a temporary file and use `git commit -F <file>`. This preserves line breaks and prevents a Git commit template from altering the message. Do not use `--no-verify` unless the user explicitly asks.
6. **Avoid assistant attribution.** Never add, suggest, or retain a `Co-authored-by:` trailer for the assistant or any identity the user did not request. Before committing, scan the complete message, including footers, case-insensitively. If it contains `Co-authored-by:`, remove it and request final approval again. Do not change Git `user.name` or `user.email` without authorization.
7. **Verify and report.** After a successful commit, run `git show -s --format=%B HEAD` and verify that the resulting commit contains no `Co-authored-by:` trailer. Report the short hash and summary. If a hook or configuration added co-authorship, say so clearly and request authorization before rewriting history to correct it.

## Boundaries

- Do not `push`, `amend`, `reset`, `rebase`, or change Git configuration unless explicitly requested.
- Respect hooks and validation failures; explain the error rather than bypassing it automatically.
- When the user requests multiple commits, separate changes by intent and request interactive approval for each commit.
- If a change may be breaking but its intent is unclear, ask before using `!` or `BREAKING CHANGE`.

## Examples

- Add API pagination: `feat(api): add cursor pagination`
- Fix a retry limit: `fix(worker): cap retry backoff`
- Breaking change: `feat(config)!: remove legacy cache option` with `BREAKING CHANGE: The legacy cache option is no longer supported.`
