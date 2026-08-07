# Specialist Question Contract

Load this reference when acting as an AIDev specialist. It is the complete specialist-side question, pause, and resume contract.

## Interaction mode

| Mode         | Behavior                                                                                                                                        |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `direct`     | You are user-facing. Ask through the host native question mechanism, then continue after the answer.                                            |
| `delegated`  | You were invoked by an agent or orchestrator. Follow this reference's envelope procedure, return the required one-line path response, and stop. |
| Mode missing | Assume `delegated` when another AIDev agent or orchestrator invoked you; otherwise assume `direct`.                                             |

## Delegated pause procedure

When you cannot safely continue without user input, write the canonical Markdown envelope from [../assets/subagent-question-envelope.md](../assets/subagent-question-envelope.md) to `{session-path}/delegations/{delegation-id}-round-{round}-questions.md`, where round starts at `1` and increments for the same delegation. Create `delegations/` if necessary. Then return exactly this plain-text line and nothing else:

`My questions are in: {session-path}/delegations/{delegation-id}-round-{round}-questions.md`

Never bury blocking questions in prose, blockers, risks, reports, or summaries.

**Batching:** include every open blocking question you can already formulate in one envelope.

## Stop reasons

| Reason                   | Stop when                                                                                                                                              |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `missing_required_input` | A mandatory value is absent and not deterministically recoverable.                                                                                     |
| `approval_required`      | A gate, decomposition, source selection, plan approval, publish/persistence action, risk acceptance, or final transition needs explicit user approval. |
| `material_assumption`    | Continuing means inventing a fact that changes scope, requirements, architecture, ordering, verification, risk, or external side effects.              |
| `ambiguous_intent`       | The intended flow, artifact, repository, or outcome has multiple plausible meanings.                                                                   |
| `external_dependency`    | Execution must wait for CI, an artifact, a human action, or an unavailable service.                                                                    |
| `artifact_problem`       | Required artifacts are missing, stale, or inconsistent with the workspace.                                                                             |
| `unsafe_action`          | The next action is irreversible or external-facing (push, publish, delete, create issues/PRs, accept risk).                                            |
| `contract_failure`       | A required sub-agent or skill returned malformed or unverifiable output.                                                                               |

Do not stop for non-material uncertainty. Record minor assumptions in your artifact and continue when they do not affect user-visible behavior, gates, external actions, or downstream agents.

## Before pausing

Persist enough state so a fresh instance can recover without chat history only when native continuation is unavailable or the original invocation can no longer be resumed:

1. Write completed work to your owned artifact.
2. Record the current phase/step, last completed step, and next step after answers.
3. Record decisions already made and their source.
4. Record pending items that remain after the answers.
5. Add invalidation checks that would make the checkpoint stale.

If you cannot identify where to resume, write an envelope with `reason: contract_failure` instead of asking from unstable context.

## Envelope requirements

- The persisted envelope is immutable after you write it. Never add answers, amend questions, or otherwise use it as a response record. Once the orchestrator validates the answers, it moves its complete context into the active request and deletes the consumed envelope atomically.
- `Delegation` remains stable across pause/resume; `Phase` is the exact lifecycle phase, never an artifact name.
- Ask one decision per stable, meaningful question heading. Use `Options` when known; mark exactly one recommended option when there is a clear recommendation.
- Use `Freeform: yes` unless only approval/decline is valid, and use `Default: none` for every blocking question.
- For validation or approval questions, put a substantive, decision-ready summary in `Context`; never point only to another artifact.
- `Progress` is durable and factual. `Preserved decisions` lists only decisions that must not be re-litigated. `Invalidate if` must be concretely evaluable.

## Resume and completion

When resumed through the generated request containing `## Resume Context`, read every listed artifact, apply each answer to the durable artifact, validate the checkpoint, then continue from the recorded next step. The request repeats the original questions, options, checkpoint, and resume contract so a fresh instance can safely continue. Do not repeat completed work.

If validation fails, pause again with `artifact_problem` or `material_assumption`; do not restart unless the checkpoint is invalid or the user asks.

Before returning `completed`, ensure no unresolved question remains, no stop reason applies, no material assumption is silent, required approvals are received, and all durable downstream artifacts are current. Otherwise, return an envelope.
