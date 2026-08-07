# Subagent Question Envelope

- **Schema:** `1.0`
- **Delegation:** `<stable id, e.g. planner.target-repo>`
- **Agent:** `<AIDev specialist name>`
- **Topic:** `<short task or topic>`
- **Phase:** `<owning SDD phase>`
- **Status:** `needs_user_input`
- **Gate:** `paused`

## Checkpoint

- **Current step:** `<paused step>`
- **Last completed:** `<last safely persisted step>`
- **Resume from:** `<exact next step after answers>`
- **Primary artifact:** `<path or none>`
- **Supporting artifacts:** `<comma-separated paths or none>`
- **Progress:** `<durable summary for continued delegated work>`

## Questions

### `<stable-question-id>`

- **Reason:** `<missing_required_input | approval_required | material_assumption | ambiguous_intent | external_dependency | artifact_problem | unsafe_action | contract_failure>`
- **Question:** `<one user decision>`
- **Context:** `<decision-ready context; include a substantive summary for approvals>`
- **Blocks:** `<phase | next step>`
- **Options:**
  - `<option-id>` — `<label>`; impact: `<outcome>`; recommended: `<yes | no>`
- **Freeform:** `<yes | no>`
- **Default:** `none`

## Resume Contract

- **Read first:** `<primary and supporting artifacts>`
- **Apply:** `<answers to the durable artifact before continuing>`
- **Completed:** `<completed items>`
- **Pending:** `<pending items>`
- **Preserved decisions:** `<decision and source>`
- **Invalidate if:** `<condition requiring re-grounding or a new question>`
