---
name: commit
description: "Trigger: commit, commitear, save changes to git. Group changes into multiple Conventional Commits and confirm the plan with the user before executing."
license: Apache-2.0
metadata:
  author: kyubiful
  version: "1.1"
---

## When to Use

- User asks to commit, "commitear", or save changes to git
- User says "haz un commit", "commit the changes", "commitea esto"
- Finalizing a feature, fix, or chore and the user wants it recorded

---

## Critical Rules

1. **NEVER add a body or description** — subject line only, no blank line + body
2. **NEVER add `Co-Authored-By` trailers** — not for Claude, not for anyone unless the user explicitly asks
3. **NEVER use `--no-verify`** — hooks must run
4. **ALWAYS group changes** — analyze all diffs and propose multiple commits when changes span different features or scopes
5. **ALWAYS show the full commit plan** before executing — list every commit with its files, then wait for a single confirmation
6. **ALWAYS stage specific files** — never `git add -A` or `git add .`
7. **NEVER commit if the user is silent or ambiguous** — explicit approval only

---

## Commit Message Format

```
type(scope): subject
```

- **type** — required: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `revert`
- **(scope)** — optional: lowercase, short, e.g. `map`, `table`, `button`, `api`
- **!** — optional: append before the colon to signal a breaking change, e.g. `feat(api)!: remove old endpoint`. No footer needed — stays compatible with rule 1 (no body/trailers)
- **subject** — required: imperative mood, lowercase start, no period at end, max ~72 chars

### Valid examples

```
feat(map): add layer visibility toggle
fix(table): correct sticky header z-index
chore(deps): bump version to 0.0.25
docs(readme): add map usage example
refactor(button): simplify variant logic
style(icons): fix lint warnings
test(dropdown): add keyboard navigation coverage
feat(api)!: remove deprecated v1 endpoints
```

### Invalid — DO NOT use

```
feat(map): Add layer visibility toggle.        ← capitalized + period
fix: fixed the button                          ← past tense + vague

Co-Authored-By: Claude <noreply@anthropic.com> ← NEVER add this
```

---

## Workflow

```
1. Run: git status + git diff (staged and unstaged)
2. ANALYZE all changed files and group them by logical unit:
   - Same feature or component (e.g., all network/* changes → one commit)
   - Same fix (e.g., layout bug affecting two files → one commit)
   - Same chore (e.g., dependency bumps, config updates → one commit)
   - Unrelated changes MUST be separate commits
3. For each group:
   a. Determine type and scope
   b. Draft subject line (imperative, lowercase, no period)
   c. List the exact files that belong to this group
4. Present the full commit plan and STOP — do not execute anything yet
5. Wait for explicit user approval, then branch:
   - **"sí" / "dale" / "ok" / "yes" / "go"** → execute all commits in order
   - **"merge 1 and 2"** → combine those groups, re-show plan, wait again
   - **"split 1"** → ask which files go where, re-show plan, wait again
   - **"no"** → ask what they want changed; never abort silently
6. Execute commits IN ORDER:
   a. git add <files for this group>
   b. git commit -m "<message>"
   c. Repeat for next group
7. After all commits: run git log --oneline -N to show the result
```

---

## Grouping Heuristics

| Signal                                                            | Rule                                                            |
| ----------------------------------------------------------------- | --------------------------------------------------------------- |
| Files under the same component or route                           | Same commit                                                     |
| Files that implement both UI and its hook/service for one feature | Same commit                                                     |
| Independent features with no shared files                         | Separate commits                                                |
| `package.json` + `package-lock.json` / `yarn.lock`                | One `chore(deps)` commit                                        |
| Test file paired with the implementation file it tests            | Same commit as the impl                                         |
| Config/env files unrelated to a feature                           | Separate `chore(config)` commit                                 |
| Layout file touched by two independent features                   | Assign to the feature that changed it more; note it in the plan |

---

## Commit Plan Format

Show this before executing anything:

```
Propongo los siguientes commits:

1. feat(network): hide columns in courier network table
   Files: app/(pages)/(protected)/network/components/courier-network-table.tsx

2. fix(map): correct marker icon on couriers map
   Files: app/(pages)/(protected)/network/components/couriers-map.tsx

3. chore(layout): update protected layout structure
   Files: app/(pages)/(protected)/layout.tsx

¿Confirmás este plan? (sí/no — o indicame qué cambiar)
```

Wait. Do NOT run any git commands until the user says yes.
