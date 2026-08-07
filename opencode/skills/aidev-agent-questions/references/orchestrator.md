# Orchestrator Question Contract

## Classify the specialist response

A delegated specialist returns exactly one of these outcomes:

- `My handoff is in: {path}`, referencing the script-generated SDD manifest.
- `My questions are in: {path}`, the delegated question response.

For the delegated question response, follow the remaining sections of this contract. Do not treat answered recommendations as a normal handoff; the same specialist must still return a manifest-path response before the phase can advance.

## Priority and SDD lifecycle

Before workspace preflight, gate validation, phase routing, or any new specialist invocation, inspect `orchestration.pending_delegation`. When it is non-null, complete this protocol first. Do not advance, validate, or route another phase while the delegation is pending.

When a specialist returns `My questions are in: {path}`:

1. Read the persisted envelope and verify that its path is within the active session's `delegations/` directory.
2. Validate its identity and blocking content: stable delegation ID, delegated specialist, current owning phase, `needs_user_input` status, paused gate recommendation, and at least one declared question.
3. For SDD, run the `pause-handoff` state operation. It validates the envelope identity against the active phase owner, then atomically records `pending_delegation`, blocks the current phase, pauses its gate, and records the question round. Specialists never run the SDD CLI or edit SDD state.
4. Immediately run the `status` state operation and verify that `pending_delegation` names the returned specialist, the current phase is `blocked`, and its gate is `paused`.

Registration is a hard precondition to user interaction: do not perform the question until both steps succeed. If registration or verification fails, report the state error and do not present the envelope. A `status` result with `unregistered_question_envelopes` is likewise a stop signal: register the returned envelope before asking any question.

Do not resolve a pending delegation until every blocking question has a concrete answer and the transient resume packet is complete.

## Present questions

1. Preserve the envelope's question order.
2. Show each question's `Context`, plus `Progress` when decision-relevant, before or alongside its question. Include declared options, the recommendation, and freeform availability so the user can decide without workspace artifacts or prior conversation.
3. Ask only the envelope's declared questions through the host native question mechanism. Do not add synthetic prompts such as “continue?” or “resume after this?”.

## Map answers

- Treat native structured selections, freeform values, and user prose as valid answers.
- If the user accepts recommendations, map each question to its sole recommended option. Ask normally when a blocking question has no recommendation.
- Map every answer to its stable question ID. Keep an unanswered question distinct from an explicit `none` or freeform answer.
- User answers authorize the next delegated specialist action. They do not authorize the orchestrator to perform specialist work inline or bypass later user gates.

## Resume the delegation

Once every blocking question has a concrete answer:

1. Run `sdd-state.py resume-handoff --expect-phase ... --answer ...` with one answer per question ID. It builds a self-contained request containing the original questions, options, checkpoint, resume contract, and answers; then atomically reactivates the phase, clears `pending_delegation`, and deletes the consumed envelope.
2. If resumption fails, keep the delegation pending and report the contract failure; do not resolve or delete the envelope.
3. Resume the original specialist instance using only the pointer prompt printed by the renderer.

The resumed request is transient handoff context, not a lifecycle artifact. It is self-contained so a fresh specialist instance can continue if native continuation is unavailable. Successful acceptance removes the request; the specialist applies durable decisions to its owned artifact.

## Failure and subsequent rounds

- If the envelope is missing, malformed, outside the session delegation directory, or inconsistent with the current SDD phase/delegation, do not register or present it. Treat it as a specialist contract failure and request a corrected envelope.
- If a user cancels, leaves a question unanswered, or supplies an unusable answer, keep the delegation pending and ask only the unresolved declared question again. Do not invent an answer or force a recommendation.
- A specialist that returns another envelope begins a new round of the same delegation. Register it with the same delegation ID only after the prior `resume-handoff` completed; the state CLI advances the round. It rejects any attempt to overwrite an unresolved pending envelope. Never merge question/answer content across rounds.
- A manifest-path response cannot resolve a pending delegation. `resume-handoff` must finish successfully before the specialist may submit a manifest.
