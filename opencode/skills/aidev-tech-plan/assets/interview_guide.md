# Deep Interview Guide

Methodology for conducting the in-depth interview during tech-plan generation. The interview runs AFTER acquiring architectural context (Step 3), consulting advisers (Step 4), and grounding everything against the live codebase (Step 5) — so you already know the stack, the architecture, have domain guidance, and have verified it all against code reality. The purpose here is to close decision gaps that only the user can resolve.

---

## Interview Dimensions

Cover the following dimensions, adapting to the specific feature. Skip dimensions clearly irrelevant based on architectural context and adviser guidance:

| Dimension                 | What to Probe                                                                                                                                                                                                               |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Behavioral contracts      | Exact expected behavior in ambiguous scenarios; what happens at boundaries                                                                                                                                                  |
| Hidden constraints        | Regulatory, compliance, team capability, timeline, budget pressures                                                                                                                                                         |
| Tradeoff tensions         | Where stated goals conflict (e.g., "fast AND flexible"); force a priority                                                                                                                                                   |
| Failure modes             | What happens when things go wrong; recovery, degradation, fallback strategies                                                                                                                                               |
| Integration surface       | How this feature touches other systems; data flow across boundaries                                                                                                                                                         |
| Contract specification    | New types, interfaces, data schemas needed; existing types being modified                                                                                                                                                   |
| Data lifecycle            | Creation, mutation, archival, deletion of data entities; consistency guarantees                                                                                                                                             |
| UX/DX decisions           | User-facing or developer-facing experience choices that shape architecture                                                                                                                                                  |
| Context-sensitive choices | Decisions where multiple valid implementation options remain after adviser guidance and grounding, and the choice materially affects architecture, maintainability, operations, UX, performance, security, or delivery risk |
| Observability             | Logging, monitoring, alerting needs that affect design                                                                                                                                                                      |
| Evolution path            | How this feature is likely to change in 6-12 months; extensibility needs                                                                                                                                                    |

---

## Question Generation Rules

For each question, verify it passes ALL of these filters before asking:

1. **NOT answerable from architectural context, adviser guidance, or codebase grounding** — if the answer is already documented, was returned by an adviser, or was verified/discovered in Step 5, skip it
2. **NOT a restatement of requirements** — never ask "Should we do X?" when X is already stated in the spec
3. **EXPOSES a hidden decision** — the answer materially changes architecture, data model, task decomposition, or UX behavior
4. **CHALLENGES assumptions** — probes what happens if an "obvious" assumption is wrong
5. **FORCES prioritization** — when two goals conflict, makes the user choose
6. **ASK when multiple grounded-valid options remain** — if adviser guidance and codebase grounding still leave more than one credible option, and the choice would materially affect implementation, escalate it to the user instead of choosing silently

### Bad Examples (do NOT ask these)

- "Should we use the existing database?" (implied by architectural context)
- "Do you want error handling?" (always yes)
- "Should we write tests?" (always yes)
- "Should we follow the project's architecture?" (already established)

### Good Examples (non-obvious, decision-forcing)

- "When the order total exceeds the credit limit mid-checkout, should the system hold the partial charge or release it entirely? This affects whether we need a two-phase commit pattern."
- "The stack shows both real-time sync and batch processing. If you had to ship with only one, which delivers more value? This determines whether we build the event pipeline or the ETL job first."
- "Current auth uses session tokens but the new API serves mobile clients. Should we migrate to JWT for this endpoint only, or globally? Local migration is faster but creates two auth paths to maintain."
- "The plan needs a new OrderEvent for cross-service communication. Should it carry the full order snapshot (~2KB fat event) or just the order ID with a callback URL (~100B thin event)? Fat events are self-contained but couple the consumer to the producer's schema."
- "We found two valid options within the same library family for this exact need. One is recommended by platform guidance for filter-toolbar usage, while the other appears in the repository but only in form contexts. Should the plan prioritize platform-recommended context fit or consistency with the nearby local precedent?"
- "For this visible filter control, the platform guidance recommends `SelectTag` for toolbar filtering, while the repository only shows `SelectField` in form flows. Do you want the plan to prioritize design-system context fit or local consistency when those differ?"
- "There is both an existing shared implementation path and a local implementation path available. Should this feature extend the shared asset for consistency, or stay local for lower coordination cost? Shared improves reuse but increases cross-team dependency."
- "The system can land this through an existing synchronous boundary or through an asynchronous integration path. Which do you want to optimize for in V1: simpler delivery now or looser coupling for future evolution?"

---

## How to Ask Questions

Use the assistant's native question/interaction mechanism to present questions to the user. Structure each question with:

- Clear, specific question text explaining the decision point
- 2-4 concrete options with a one-line explanation of implications for each
- Your recommended option clearly marked (put it first, label it as recommended)
- Group up to 4 related questions per interaction round

The goal is that the user can answer quickly by selecting an option or providing a brief response — not write essays.

---

## Interview Loop

```
ROUND = 1
REPEAT:
  a. Review architectural context, adviser guidance, codebase grounding findings, and any prior answers from this interview
  b. Assess which dimensions remain uncovered or have unresolved ambiguity
  c. Generate 2-4 questions targeting uncovered dimensions (apply the generation rules strictly)
  d. Present questions to the user and wait for answers
  e. Record each answer in tech-plan.md under ## Design Decisions
     Format: - **[Dimension]**: Q: <question> → A: <answer>
  f. Save the plan file after each round
  g. ROUND = ROUND + 1

  EXIT CONDITIONS:
  - If ROUND >= 3 AND all relevant dimensions are covered:
    Ask the user: "I've covered the key dimensions. Are there concerns or
    tradeoffs I haven't asked about, or shall we proceed to write the plan?"
    Options: "Proceed to planning" / "I have more to discuss"
    If user selects "Proceed": EXIT loop
    If user selects "I have more to discuss": CONTINUE with follow-up

  - If ROUND < 3: CONTINUE (minimum 2 full rounds before offering to end)
END REPEAT
```

---

## Recording Design Decisions

After each round, immediately:

1. Append each answer to the `## Design Decisions` section of `tech-plan.md`
2. Use the format: `- **[Dimension]**: Q: <question> → A: <answer>`
3. If an answer changes assumptions made in earlier steps (spec interpretation, adviser guidance applicability), note the impact inline
4. Save the file — this persists progress even if the conversation is interrupted

The Design Decisions section becomes a traceable record that connects user intent to architectural choices in the Implementation Plan.
