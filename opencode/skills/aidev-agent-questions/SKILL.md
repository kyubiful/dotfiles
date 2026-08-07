---
name: aidev-agent-questions
description: Question, pause, and resume protocol for AIDev specialists and orchestrators.
---

# AI Dev Questions

Load exactly one role contract before handling a question flow:

| Role         | Load                                                     |
| ------------ | -------------------------------------------------------- |
| Specialist   | [references/specialist.md](references/specialist.md)     |
| Orchestrator | [references/orchestrator.md](references/orchestrator.md) |

The specialist contract owns immutable envelope creation, pause conditions, and safe resumption. The orchestrator contract owns question presentation, answer mapping, and resume-target selection. In SDD, `resume-handoff` constructs the self-contained request and applies the state transition atomically. A workflow-specific invocation contract owns the request shape.

## Resources

| Asset                                                                        | Purpose                                                   |
| ---------------------------------------------------------------------------- | --------------------------------------------------------- |
| [assets/subagent-question-envelope.md](assets/subagent-question-envelope.md) | Canonical immutable persisted question-envelope template. |
| [references/specialist.md](references/specialist.md)                         | Complete specialist contract.                             |
| [references/orchestrator.md](references/orchestrator.md)                     | Complete orchestrator contract.                           |
