# SDD Specialist Handoff Commands

All specialist requests, resumes, and manifests use the assistant-local `sdd-state.py` CLI. Generated requests preserve the specialist-resolved `<agent-dir>` placeholder and portable workspace-relative paths.

## Initial delegation

```bash
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py create-handoff \
  {session-dir} --expect-phase {phase} --need "{required outcome and user scope}" \
  [--context {path} "{why it matters}"]... \
  [--policy {key} "{value}"]...
```

The command writes `{session-dir}/handoffs/requests/{phase}.md` and prints the exact pointer prompt to send to the specialist unchanged.

## Question pause and resume

When a specialist returns an envelope, register it:

```bash
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py pause-handoff \
  {session-dir} {phase} {agent} {delegation-id} {envelope-path}
```

After every declared question has an answer, resume it:

```bash
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py resume-handoff \
  {session-dir} --expect-phase {phase} \
  --answer {question-id} {selected-option-or-none} "{answer}" \
  [--answer ...]
```

`resume-handoff` validates the envelope and all answers, rebuilds the request from its trusted base with a self-contained resume context, clears `pending_delegation`, restores the phase to `in-progress`, and deletes the consumed envelope in one transaction. The request preserves the original questions, options, checkpoint, resume contract, and answers so a fresh specialist can continue without chat history.

## Validation retry

When `validate-handoff` reports deterministic findings, preserve the active request and materialize a correction request:

```bash
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py retry-handoff \
  {session-dir} --expect-phase {phase} \
  --finding "{reported finding}" [--finding "{reported finding}" ...]
```

`retry-handoff` requires an active delegated phase with no pending question envelope. It retains the active request, including any `Resume Context`, replaces only its validation-remediation section, and updates the trusted request base so a later question resume retains those findings. It deletes the stale phase manifest without advancing lifecycle state. Continue the original specialist using only the printed pointer prompt. When native continuation is unavailable, a fresh same-type specialist receives that identical pointer; never replace this operation with a free-text correction task.

## Specialist result

The generated request contains a phase-specific command of this form:

```bash
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py submit-handoff \
  {session-dir} --expect-phase {phase} --status {ready|blocked} [phase-specific flags]
```

It writes and validates the minimal YAML manifest and prints:

`My handoff is in: {workspace-relative-manifest-path}`

The specialist returns that line unchanged. The orchestrator then validates and accepts it with `validate-handoff` and `accept-handoff`.
