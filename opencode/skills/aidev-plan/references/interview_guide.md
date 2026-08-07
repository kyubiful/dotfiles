# Deep Interview Guide

This guide defines the methodology for conducting the in-depth interview during the planning phase. The interview runs BEFORE spec definition — its output directly informs all subsequent planning steps.

When previous research exists, the interview builds on top of validated findings. Do NOT re-ask questions already answered in the research session file — focus on uncovering what research could not capture: hidden decisions, tradeoff priorities, and implementation-shaping constraints.

---

## Interview Dimensions

The interview probes three tiers of dimensions. **Primary dimensions** are product-facing — they capture what users care about and how they'll judge the work. These must be explored in every interview and drive the first rounds. **Secondary dimensions** are engineering-facing — they capture what builders need. These are explored when relevant, typically in later rounds. **Tertiary dimensions** are business-strategy-facing — they capture success measurement, stakeholder alignment, rollout planning, and future evolution. These are explored when the work is product/business-oriented and may be skipped for purely technical work (bugs, spikes, tech improvements).

Leading with product dimensions prevents a common failure mode: engineering-heavy interviews generate engineering-informed ACs, and specs become implementation prescriptions instead of product contracts. Product questions also surface hidden decisions and boundary cases more naturally — a concrete user walkthrough reveals more gaps than an abstract "what's the data lifecycle?" question.

### Primary — Product (always probe, rounds 1-2)

| Dimension            | What to Probe                                                                                                                                                                                                                                                                                              |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User Journey         | Walk through the feature end-to-end with a **real example**. Who does what, in what order, what do they see at each step? Include the entry point, the core interaction, and the end state. For UI features, probe what the user sees; for API/backend features, probe what the caller sends and receives. |
| Done Criteria        | How does the user (or caller) know this is working? **What would you personally test** to be confident it's done? Push for concrete pass/fail scenarios — "give me a specific case where this succeeds and one where it should fail." These become acceptance criteria directly.                           |
| Scope Boundaries     | What should this feature **NOT** do? Where is the line between this work and adjacent work? Any organizational constraints that narrow scope — timeline pressure, compliance requirements, cross-team coordination, delivery priority (blocking? urgent? schedulable?)?                                    |
| Behavioral Contracts | Exact expected behavior in **ambiguous** scenarios. When the user does X in context Y, what exactly should they see? Focus on cases where two reasonable implementations would behave differently.                                                                                                         |
| Tradeoff Tensions    | Where stated goals conflict (e.g., "fast AND flexible"); force a priority decision. Which quality matters more when you can't have both?                                                                                                                                                                   |

### Secondary — Engineering (probe when relevant, rounds 2+)

| Dimension           | What to Probe                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Integration Surface | What information needs to be available across product capabilities? Which capabilities produce it, which consume it? For features that aggregate or list across entities, probe expected cardinality (10s, 100s, 1000s) — this shapes user experience and feasibility at the product level.                                                                                                                                               |
| Failure & Recovery  | What does the **user see** when things go wrong? What's the recovery path from the user's perspective? Not "what happens when the DB is down" but "what does the user experience when the operation can't complete?" Feeds the spec's `Error Scenarios`.                                                                                                                                                                                  |
| Data Lifecycle      | Creation, mutation, archival, deletion of data entities from the user's perspective; when a user makes a change, how quickly must it be visible elsewhere? What happens if information is temporarily out of date? For bugs/fixes, existing-state remediation (accumulated bad data to repair, or prevent-only?)                                                                                                                          |
| Operational Needs   | What does the team need to observe to know this feature is working correctly in production? Extensibility requirements; what's needed to maintain this long-term? **Quality attributes**: are there performance targets, capacity limits, or SLAs this feature must meet? If the user states a vague quality expectation ('fast', 'reliable'), probe for a concrete threshold — a quality attribute without a measurable target is a gap. |

### Tertiary — Business Strategy (probe for product/business-oriented work, rounds 2+)

These dimensions capture how the work connects to business outcomes, organizational alignment, and long-term strategy. They are especially valuable for features, epics, and product-oriented user stories. They may be skipped for purely technical work (bug fixes, spikes, tech improvements) where business strategy dimensions add no actionable information.

| Dimension          | What to Probe                                                                                                                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Success Metrics    | How will we measure if this feature is successful? What KPIs matter? What does "good" look like in numbers? Probe for concrete targets — "increase conversion" is a wish; "increase checkout completion from 60% to 75%" is a measurable target.  |
| Stakeholder Needs  | Who else cares about this feature beyond the direct user? (operations, legal, finance, customer support, partner teams) What do they need from it? Are there conflicting stakeholder priorities that need resolution?                             |
| Rollout & Adoption | How should this be rolled out? All users at once or gradual? Is there a feature flag strategy, a beta group, or a market-by-market rollout? What's the adoption strategy — does the user need to be taught, or is this a transparent improvement? |
| Future Evolution   | How is this likely to evolve in the next 6–12 months? What should we design for extensibility vs. what is explicitly a one-time solution? Are there planned follow-ups that should influence today's scope boundaries?                            |

### Type-aware probing

Not all work types surface the same gaps. After covering general product dimensions, adapt your probing to the specific work type:

- **Bugs / Fixes**:
  - _User Journey_: Walk through the reproduction steps — what does the user do, what do they see, where does it break?
  - _Done Criteria_: How do you know the fix worked? What would a regression look like?
  - _Scope Boundaries_: Fix this one case or all similar cases? Repair accumulated bad data or prevent-only going forward?
  - _Failure & Recovery_: What's the blast radius — who/what is affected today?

- **Spikes / Research**:
  - _Done Criteria_: What's the concrete deliverable? (Document, proof of concept, decision recommendation — not just "research done")
  - _Scope Boundaries_: What decision is blocked by this uncertainty? What's the timebox?
  - _Tradeoff Tensions_: If the research is inconclusive, what's the fallback decision?

- **Features with multi-spec potential**:
  - _Scope Boundaries_: What's the minimum that delivers value (MVP)? What's explicitly deferred?
  - _User Journey_: Which user journey is the MVP? Which journeys can wait?
  - _Done Criteria_: What would you test for the MVP specifically?

### Multi-artifact considerations

When the plan spans multiple artifacts (microservices, SPAs, libraries), pay special attention to:

- **Scope Boundaries**: Which artifact owns which responsibility? Where does one artifact's job end and another's begin?
- **Integration Surface**: API contracts between artifacts, event schemas, shared data models
- **Tradeoff Tensions**: When an optimal choice for one artifact creates friction for another
- **Failure & Recovery**: Cascading failures across artifact boundaries; what does the user experience when an upstream dependency fails?
- **Data Lifecycle**: Data ownership and consistency across services (eventual vs strong consistency)

---

## Concrete Examples Drive Specs

The most effective interview technique is asking for **concrete examples**, not abstract requirements. This draws from BDD's Example Mapping: features have rules (abstract constraints) and examples (concrete scenarios). **Examples, not rules, produce the best acceptance criteria.**

When the user says:

- ❌ "It should handle errors gracefully" → This becomes a vague, untestable AC
- ✅ "When the API returns 500, the user sees 'Service temporarily unavailable' and can retry" → This becomes a testable AC

**During the interview, push for concrete examples whenever the user gives an abstract statement.** Ask: "Can you walk me through what that looks like?" or "Give me a specific scenario where that matters."

The **Done Criteria** dimension is specifically designed to elicit these examples. The user's answers to "what would you personally test?" produce ACs that are:

1. **Behavioral** — what the user sees, not what the system does internally
2. **Concrete** — specific scenario, not abstract quality
3. **Testable** — clear pass/fail, not subjective judgment

---

## Functional Work-Breakdown

Alongside the dimensions, keep a running **functional** hypothesis of the work this idea implies — recorded in `## Work Breakdown` in the session file, refined each round. This closes the gap so the issue projection (Phase 3, Step 7) can propose a concrete issue list without re-interviewing.

Track three things, in product language only — **never** components, endpoints, or technical tasks:

- **Units of work** — discrete user-facing outcomes (candidate user-story issues).
- **Open questions** — uncertainties that block or shape delivery. Classify each by what it would take to close it:
  - _Functional/purpose_ — what the product should do, for whom, and why (scope, behavior, success criteria). Resolvable by the user/PO, so **drive it to resolution in this interview**; it never becomes a backlog item.
  - _Feasibility/how_ — cannot be answered by conversation; needs investigation or experimentation to produce a decision (e.g. viability of an external integration, availability of source data). This is the only open question that survives as a **candidate spike** — one that frames WHAT must be investigated and WHY, leaving the HOW to `aidev-tech-plan`.
- **Defects** — broken behavior surfaced along the way (candidate bug issues).

Use it to drive questioning: when a unit's boundary or a functional/purpose open question is fuzzy, that is your next question. By the exit offer, every functional/purpose open question is resolved and every unit has enough context to become an issue.

Two dimensions feed the spec's non-happy-path sections directly: **Failure & Recovery** answers → the spec's `Error Scenarios`; boundary/**Behavioral Contracts** answers → the spec's `Edge Cases`.

---

## Complexity Triage

Before starting the interview, classify the input quality to calibrate the depth of discovery. This prevents over-interviewing well-defined inputs and under-interviewing vague ones.

| Input Quality           | Description                                                                                   | Recommended Rounds | Focus                                                                                                                        |
| ----------------------- | --------------------------------------------------------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| **Well-defined**        | Detailed research handoff, structured brief with clear scope, personas, and concrete examples | 1–2                | Only fill gaps: edge cases, behavioral contracts, unresolved open questions. Probe business-strategy dimensions if relevant. |
| **Moderately defined**  | Clear idea with some context but missing business rules, edge cases, or boundary definitions  | 2–3                | Business rules, edge cases, done criteria, scope boundaries. Add business-strategy dimensions for product-oriented work.     |
| **Vague / exploratory** | High-level idea, one-liner, or broad need without specifics                                   | 3–4                | All relevant dimensions across all tiers, starting with user journey and done criteria.                                      |

**Apply this triage at the start of Phase 2.** Announce your assessment to the user: _"Based on the context so far, this looks [well-defined / moderately defined / vague]. I expect around [N] rounds of questions."_

This sets expectations, prevents over-interviewing, and makes the process transparent to the user. The triage is a guideline, not a hard cap — if new gaps emerge during later rounds, continue until you have sufficient context for well-defined specs.

---

## Question Generation Rules (Non-Obvious Questions Only)

For each question, verify it passes ALL of these filters before asking:

1. **NOT answerable from available context** — if the answer is already in the research handoff, exploration context, or previous interview rounds, skip it
2. **NOT a restatement of requirements** — never ask "Should we do X?" when X is already stated
3. **EXPOSES a hidden decision** — the answer materially changes spec definition, artifact assignment, or cross-artifact contracts
4. **CHALLENGES assumptions** — probes what happens if an "obvious" assumption is wrong
5. **FORCES prioritization** — when two goals conflict, makes the user choose

### Bad Examples (obvious — do NOT ask these)

- "Should we use the existing database?" (already implied by context)
- "Do you want error handling?" (always yes)
- "Should we write tests?" (always yes)
- "Do you want the feature to be performant?" (always yes)
- "Should we follow AMIGA framework conventions?" (always yes — it's corporate standard)
- "Do you want to use DevHub for discovery?" (already part of the workflow)

### Good Examples (non-obvious, insightful)

**Product-primary** (these reveal what the feature actually means):

- "Walk me through what happens when a user selects 3 code sources and 2 doc sources at once. Does each source go to a specific tool automatically, or does the user choose which tool gets which?" _(User Journey)_
- "You said this should work for both existing and new tools. If there's no tool of the needed type in the Space, what does the user see — a warning, an option to create one, or is the operation blocked entirely?" _(Done Criteria — pass/fail scenario)_
- "The description includes 'manage sources across tools.' Does that include moving a source from one tool to another, or only adding and removing?" _(Scope Boundaries)_
- "When two tools of the same type exist and the user adds a source, which tool gets it — system picks, or user picks? And if system picks, by what rule?" _(Behavioral Contracts)_
- "Users want source selection in a single step, but showing all sources from all tools at once could be overwhelming with 50+ items. One list or grouped by tool? Convenience vs. clarity — which wins?" _(Tradeoff Tensions)_

**Engineering-secondary** (these refine how it's built):

- "The feature affects both `spa-xxxx` and `wsc-yyyy`. When catalog data changes, should search update synchronously (consistent but slower) or via events (faster but eventually consistent)? This shapes whether we need an event stream." _(Integration Surface)_
- "The rollout plan mentions feature flags. If the flag is disabled mid-transaction for a user who already started, should the system complete with the new flow or fall back to the old one?" _(Failure & Recovery)_
- "This feature needs to work across 3 brands. Should we build brand-specific behavior via configuration (one artifact, multiple configs) or separate deployments? Config is cheaper but harder to diverge later." _(Tradeoff Tensions — engineering angle)_

**Business-strategy** (these connect the work to business outcomes):

- "You mentioned increasing conversion as a goal. What's the current checkout completion rate, and what target would make this feature a success? Without a concrete number, we can't write a meaningful success criterion." _(Success Metrics)_
- "Customer support will need to handle edge cases from this feature. Have they been consulted? Do they need new tooling, scripts, or training to support it — and does that affect our timeline?" _(Stakeholder Needs)_
- "This changes the checkout flow for all users. Should we roll it out to a beta group first, or go live for everyone? If beta, what defines the group — market, user segment, percentage?" _(Rollout & Adoption)_
- "You mentioned a loyalty integration as a possible follow-up. Should we design the data model to accommodate loyalty tiers now, or is it acceptable to refactor later? Designing for it now adds scope but reduces future rework." _(Future Evolution)_

---

## How to Ask Questions

Present each round's questions using the **assistant's native interactive question tool** (e.g., `AskUserQuestion` in Claude Code, equivalent tools in OpenCode, Copilot CLI). This creates a comfortable, focused interview: the user selects from structured options or chooses "Other" to provide freeform context. Label each question's header with its dimension (e.g., `"User Journey"`, `"Scope"`). Offer 2–4 options per question representing the most likely answers — when you have a clear recommendation, place it first. Use `multiSelect` only when choices are genuinely non-exclusive.

Questions that are inherently open-ended and resist being captured in multiple-choice options (e.g., "Walk me through the user journey step by step") may be asked as **plain text in chat** instead — but this is the exception, not the default.

**Dependent questions**: When a question's framing depends on the answer to a previous one (e.g., "if you chose caching, what invalidation strategy?"), hold it back for the next round rather than presenting it in the same round.

Structure each question with:

- Clear, specific question text referencing a concrete scenario
- Enough context for the user to understand implications
- A recommended direction when you have a clear preference

Group questions by related dimensions when possible — this helps the user reason about connected decisions together.

---

## Interview Loop Mechanics

### Dimension loop

```
TRIAGE_ROUNDS = complexity triage result (see §Complexity Triage)
ROUND = 1
REPEAT:
  a. Review all available context: research handoff (if exists), product context, and any prior answers
  b. Identify 3-4 questions targeting uncovered dimensions and fuzzy work-breakdown items
     - Rounds 1-2: Prioritize PRIMARY dimensions (User Journey, Done Criteria,
       Scope Boundaries, Behavioral Contracts, Tradeoff Tensions)
     - Round 2+: Mix in SECONDARY dimensions (Integration Surface, Failure & Recovery,
       Data Lifecycle, Operational Needs) and TERTIARY dimensions (Success Metrics,
       Stakeholder Needs, Rollout & Adoption, Future Evolution) when relevant.
       Tertiary dimensions are especially valuable for product/business-oriented
       features; skip them for purely technical work (bug fixes, spikes).
  c. Present all round questions using the assistant's native interactive
     question tool, labeling each with its dimension (e.g., header: "User Journey").
     Dependent questions: hold back any question whose framing depends on
     a prior answer and present it in the next round.
  d. Wait for the user to answer all questions before proceeding
  e. Record each answer in session file under ## Clarifications section
     Format: - **[Dimension]**: Q: <question> → A: <answer>
  f. Save the session file
  g. Update dimensional coverage assessment and the `## Work Breakdown` (units, open questions, defects)
  h. ROUND = ROUND + 1

  EVALUATE: Do I have enough context to write well-defined specs
  with clear acceptance criteria for every work item?

  IF YES AND ROUND > TRIAGE_ROUNDS: EXIT loop
  IF YES AND ROUND <= TRIAGE_ROUNDS: EXIT loop (triage is a guideline, not a cap —
     if coverage is genuinely complete, don't pad with filler questions)
  IF NO: CONTINUE with next round
END REPEAT
```

**Adapting to research input:**

When a research handoff exists:

- **Round 1**: Focus on product dimensions that research couldn't capture — User Journey walkthroughs, Done Criteria pass/fail examples, Scope Boundaries. Also probe open questions from the research (`### Open Questions` section).
- **Round 2+**: Move to Behavioral Contracts, Tradeoff Tensions, then secondary and tertiary dimensions as needed.

When no research exists (idea or direct requirement):

- **Round 1**: Start with User Journey and Done Criteria — concrete examples that ground everything else.
- **Round 2+**: Move to Scope Boundaries, Behavioral Contracts, Tradeoff Tensions. Then secondary and tertiary dimensions.

### Synthesis pass (runs exactly once, after the dimension loop exits)

Before offering to end the interview, step back from the dimensions and think about the answers as a whole:

1. **Review all answers as a set.** Look for: contradictions between answers, implications of one answer that haven't been confirmed by another, decisions with unstated consequences.
2. **Product owner test: "If a product owner read the specs I'm about to write, what would they question?"** Each question is a gap. Each gap is a candidate follow-up.
3. **Self-ask: "If I had to write the specs right now, what would I be guessing about?"** Each guess is a candidate question.
4. If steps 1-3 produced questions, present them as **one final round** using the interactive question tool. Record the answers. Then proceed to the exit offer.
5. If no questions were produced, proceed directly to the exit offer.

### Exit offer

Present a short exit question using the interactive question tool **with choices** (not freeform text):

Question: _"I've covered the key dimensions. Would you like to continue the interview or move on to spec definition?"_

- "Move on to spec definition"
- "I have more to discuss"

**If "Move on to spec definition"**: Exit the interview. Move to the next phase.

**If "I have more to discuss"**: Switch to conversational mode — the user drives. After each user input, acknowledge it, record the information in the Clarifications section, and ask "Anything else?" as lightweight conversational text (not a structured question tool). When the user signals they're done (e.g., "that's all", "let's proceed", "no"), move to the next phase.

---

## Recording Clarifications

After each round:

1. Record each answer in the session file under `## Clarifications` section
2. Format: `- **[Dimension]**: Q: <question> → A: <answer>`
3. Group by interview session date if multiple sessions occur
4. Update affected sections of the plan immediately (if specs already exist, they should reflect new decisions)
5. Save the session file after each integration

**IMPORTANT**: Wait for user answers before continuing. Do not proceed with assumptions.
