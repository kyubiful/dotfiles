---
name: jira-cloud
description: Connect safely to Jira Cloud to search, read, create, edit, comment on, assign, transition, or log work on issues. Use this skill whenever the user mentions Jira, an issue key such as PROJ-123, backlog, sprint work, tickets, or asks to manage project work—even if they do not explicitly say "Jira." Read issue data and return a task-appropriate summary; before every write, show the exact target and payload and require interactive `ask_user_question` approval. Use Jira Cloud REST credentials only from environment variables; never save, expose, or commit tokens.
compatibility: Requires Node.js 24+ with TypeScript type stripping, network access to Jira Cloud, and JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables.
---

# Jira Cloud

Use Jira Cloud REST API v3 through the resource-oriented client in `scripts/jira/`. For shell operations, use `scripts/jira.ts`, which delegates to `JiraClient` methods such as `jira.issue.get()`, `jira.comment.add()`, and `jira.search.issues()`. Run TypeScript with Node's built-in type stripping; no packages need to be installed. Credentials are read only from environment variables and the API token is redacted from output.

## Connection setup

Require these variables in the active shell:

```bash
export JIRA_BASE_URL="https://your-site.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="..."
```

- Create an API token in the user's Atlassian account; never use an account password.
- Do not write these values to a repository, `.env`, skill file, log, payload, or chat response.
- Before the first operation in a session, verify access with:

```bash
node --experimental-strip-types <skill-path>/scripts/jira.ts myself
```

If credentials are absent or the request fails, explain how to set them without asking the user to paste a token into chat.

## Resource operations

Prefer resource commands over raw REST paths:

| Intent | Command |
| --- | --- |
| Read issue | `issue.get --issue <KEY> [--data <options-json>]` |
| Create issue | `issue.create --data-file <payload-file>` |
| Edit issue | `issue.update --issue <KEY> --data-file <payload-file>` |
| Assign or unassign | `issue.assign --issue <KEY> --account-id <ID-or-null>` |
| List transitions | `issue.transitions --issue <KEY>` |
| Transition issue | `issue.transition --issue <KEY> --transition <ID> [--data-file <options-file>]` |
| List comments | `comment.list --issue <KEY> [--data <options-json>]` |
| Add comment | `comment.add --issue <KEY> --data-file <adf-document-file>` |
| Update comment | `comment.update --issue <KEY> --comment <ID> --data-file <adf-document-file>` |
| Remove comment | `comment.remove --issue <KEY> --comment <ID>` |
| Add worklog | `worklog.add --issue <KEY> --data-file <payload-file>` |
| Search issues | `search.issues --data-file <search-file>` |

Invoke a command as:

```bash
node --experimental-strip-types <skill-path>/scripts/jira.ts <command-and-options>
```

Use `raw.get`, `raw.post`, `raw.put`, or `raw.delete` with `--path` only when no resource operation exists, for example when reading edit metadata. Raw POST and PUT commands require `--data` or `--data-file`.

## Read operations

- Read only the fields needed. Pass issue options as JSON, for example `--data '{"fields":["summary","status"]}'`.
- Search with `search.issues` and a JSON object containing `jql`, `fields`, and a bounded `maxResults`. Ask for missing project, status, assignee, or time range rather than guessing a broad query.
- Read transitions with `issue.transitions` before proposing a workflow change.
- Use `raw.get --path <relative-rest-path>` to inspect edit metadata or unsupported resources. A raw path must begin with `/` and must not contain a scheme or host.

For ordinary lookup results, return a compact table with key, summary, status, priority, assignee, and URL. Include description, comments, links, or full fields only when useful. Clearly distinguish facts returned by Jira from your own summary.

## Programmatic client

Reusable TypeScript code can import `JiraClient` from `scripts/jira/index.ts`:

```ts
import { JiraClient } from "<skill-path>/scripts/jira/index.ts";

const jira = JiraClient.fromEnvironment();
const issue = await jira.issue.get("PROJ-123", {
 fields: ["summary", "status", "priority", "assignee"],
});
const results = await jira.search.issues({
 jql: "project = PROJ ORDER BY created DESC",
 fields: ["summary", "status"],
 maxResults: 25,
});
```

The available groups are `jira.issue`, `jira.comment`, `jira.worklog`, and `jira.search`. Generic `jira.get()`, `jira.post()`, `jira.put()`, and `jira.delete()` methods are available only as fallbacks for endpoints without a resource wrapper. Programmatic writes follow the same inspection and final-approval requirements as shell writes.

## Write operations

Writes include creating or editing an issue, adding or removing a comment, assigning, transitioning, and logging work. **Every write requires final approval with `ask_user_question`, even when the user asked for it directly.**

The active Pi **orchestrator** owns that approval and the final write. A delegated subagent may inspect data and prepare a proposed method, target, and payload, but must neither ask the user for approval nor execute a write. It returns its proposal to the orchestrator, which presents the interactive choice and resumes the operation only after explicit approval.

1. Inspect the target issue, project conventions, available issue types, required fields, and transitions as applicable.
2. Build the minimal JSON required by the selected resource method in a temporary file. Do not alter fields the user did not ask to change. For `comment.add` and `comment.update`, the file contains the ADF document itself; the client adds Jira's `{ "body": ... }` wrapper.
3. Return or show the issue key or project, a concise change summary, the resource method, and the complete proposed JSON payload. For assignment, include the exact account ID and display name. For transition, include the current status, target status, and transition ID.
4. The orchestrator uses `ask_user_question` immediately before executing the command, offering **Apply change**, **Edit request**, and **Cancel**. Do not treat ambiguous text as approval.
5. After approval, the orchestrator executes exactly the reviewed resource command and payload. Confirm the resulting issue key, URL, and changed fields. If Jira rejects the request, report the response and do not silently retry with different data.
6. Remove temporary payload files after the operation when they are no longer needed.

Jira Cloud REST v3 uses Atlassian Document Format (ADF) for rich-text fields such as descriptions and comments. Build valid ADF rather than sending Markdown or a bare string.

## Safety boundaries

- Never print, store, commit, or include `JIRA_API_TOKEN` in a command, payload, error report, or generated file.
- Only the active orchestrator performs a write, and never before its final interactive approval; repeat approval separately for each issue or independent write.
- Delegated subagents prepare and report proposals only. They do not ask for approval, call `ask_user_question`, or run a Jira write command.
- Do not delete issues, projects, boards, sprints, attachments, or comments unless the user explicitly requests deletion. Always request confirmation again for deletion.
- Do not bulk-edit results by default. List the targeted issues and obtain approval for the exact set and payload first.
- Do not change workflows, permissions, scheme settings, or project configuration unless explicitly requested.

## Examples

Read `PROJ-123` with selected fields:

```bash
node --experimental-strip-types <skill-path>/scripts/jira.ts \
  issue.get --issue PROJ-123 \
  --data '{"fields":["summary","status","priority","assignee","description"]}'
```

Search open bugs using a prepared file:

```json
{
  "jql": "project = PROJ AND type = Bug AND statusCategory != Done ORDER BY priority DESC",
  "fields": ["summary", "status", "priority", "assignee"],
  "maxResults": 25
}
```

```bash
node --experimental-strip-types <skill-path>/scripts/jira.ts \
  search.issues --data-file <search-file>
```

Create a bug only after final approval, using this issue payload:

```json
{
  "fields": {
    "project": {"key": "PROJ"},
    "issuetype": {"name": "Bug"},
    "summary": "Prevent duplicate retry jobs"
  }
}
```

```bash
node --experimental-strip-types <skill-path>/scripts/jira.ts \
  issue.create --data-file <payload-file>
```
