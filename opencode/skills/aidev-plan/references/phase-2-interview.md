# Phase 2 — Deep Interview

> This file contains the complete instructions for Phase 2. Do not read other phase instruction files until this phase's gate is met.

Before defining specs, conduct an in-depth interview to surface requirements, constraints, tradeoffs, and design decisions that cannot be captured from research or initial input alone.

Follow the complete interview methodology in [interview_guide.md](interview_guide.md), which covers:

- **Complexity Triage** — classify input quality to calibrate interview depth (well-defined → 1–2 rounds, moderate → 2–3, vague → 3–4)
- **Interview Dimensions** — 3 tiers: 5 product-primary (user journey, done criteria, scope boundaries, behavioral contracts, tradeoff tensions), 4 engineering-secondary (integration surface, failure & recovery, data lifecycle, operational needs), and 4 business-strategy (success metrics, stakeholder needs, rollout & adoption, future evolution)
- **Concrete Examples Drive Specs** — push for concrete pass/fail scenarios that become acceptance criteria directly
- **Question Generation Rules** — 5 filters every question must pass to ensure non-obvious, insightful questions
- **Interview Loop Mechanics** — iterative loop calibrated by the complexity triage

**Key rules**:

- **Start with a complexity triage**: Before asking the first question, classify the input quality and announce your assessment and expected interview depth to the user. See the Complexity Triage section in the interview guide.
- Every question must EXPOSE a hidden decision, CHALLENGE assumptions, or FORCE prioritization — never ask obvious questions
- If research exists, DO NOT re-ask what is already answered in the research handoff — build on top of it
- Present each round's questions using the **assistant's native interactive question tool** — this creates a focused, comfortable interview where the user clicks through structured choices or elaborates via "Other" when needed, rather than parsing a wall of numbered questions. See the "How to Ask Questions" section in the interview guide for format details, question design, and when to complement with freeform follow-ups. Hold back dependent questions for the next round
- Record each answer in the session file under `## Clarifications` with format: `- **[Dimension]**: Q: <question> → A: <answer>`
- Update the session file after each round — do NOT wait until the interview ends
- **Maintain a functional work-breakdown**: each round, update `## Work Breakdown` in the session file with the units of user-facing work and open questions the answers imply — strictly WHAT/why, never technical tasks. Use it to sharpen the next round's questions and to seed the issue projection (Phase 3, Step 7). See the interview guide.
- If you consult additional sources (SDD specs, product MCP tools, API docs, code) to inform interview questions, add them to `### Sources consulted` in `## Product Context`
- Set status to `🔄 Interview` while this phase is active
- Do NOT proceed to Phase 3 until the interview loop has completed
- After the final round, explicitly ask the user to confirm they are ready to move to spec definition phase. If the feature has visible UI, also offer to generate a prototype (SewingAI) during spec authoring: mention it as a one-line option alongside "Move on to spec definition" — do not elaborate unless the user asks. Make this proactive offer only when the execution mode is interactive; if the state is not interactive, do not surface it.

## Gate

When the interview loop is complete:

- Complexity triage assessment communicated to the user at interview start
- Interview rounds completed (count calibrated by complexity triage — see interview guide)
- Clarifications recorded in session file
- User selected "Move on to spec definition" in the exit offer

Announce: **"Phase 2 complete. Proceeding to Phase 3 — Spec Definition."** Then continue reading `phase-3-specs.md`.
