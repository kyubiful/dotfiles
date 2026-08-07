# SDD Retro

> Closing journal for the session. It records what the session **observed** and what it **decided to compound** into the target product, so the next iteration on the same product is cheaper. Its value lives in the side effects it logs (enriched product docs, consolidated specs); this file is the auditable ledger of those decisions, not a team retrospective.

## Topic

| Field            | Value                |
| ---------------- | -------------------- |
| Topic            | example-topic        |
| Closure evidence | verification.md, ... |
| Closure status   | complete             |

## Outcome Summary

One short paragraph: what was delivered, whether the approved spec was satisfied, and whether the session can close.

## Observations

What this session surfaced that a future iteration on this product would otherwise rediscover the hard way: product/domain behavior, architecture, contracts, code constraints, and tacit decisions with their rationale. Keep every entry about the product; never record observations about the SDD framework, its phases, agents, gates, or tooling. Write `None` when nothing durable surfaced.

| ID    | Area     | Observation                                                                                                              | Evidence                         |
| ----- | -------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------- |
| OBS-1 | Frontend | Time-based UI state must be re-evaluated as the clock advances while the view stays mounted, not only when data changes. | todo-dashboard reminder behavior |

### Dead Ends & Rejected Approaches

Negative knowledge: approaches that were tried or assumed and failed. Each row should let a future agent avoid re-exploring the same failed path. Write `None` when there were no dead ends.

| ID        | Approach Tried                | Why It Failed                                               | Correct Approach   |
| --------- | ----------------------------- | ----------------------------------------------------------- | ------------------ |
| DEADEND-1 | What was attempted or assumed | Observable reason it failed (link the AC, finding, or test) | What to do instead |

## Compounding Ledger

The core of this journal: each durable observation the session decided to write into the product context resources future agents already read. Only specs are compounded; the rest stay as observations above. Every compounded note is phrased as native product engineering knowledge and must not mention SDD, its phases, agents, gates, or this session's machinery. Write `None` when nothing was compounded.

| ID     | Source            | Durable Knowledge                                                        | Target Surface               | Section               | Status                                     |
| ------ | ----------------- | ------------------------------------------------------------------------ | ---------------------------- | --------------------- | ------------------------------------------ |
| KNOW-1 | OBS-1 / DEADEND-1 | One-line product rule a future agent must know, written in product terms | repos/<repo>/ARCHITECTURE.md | Constraints & Gotchas | applied \| skipped-duplicate \| kept-local |

## Spec Consolidation

Canonical specs the session created, updated, or retired. Creates/updates have a matching `changes/changes.json` entry and per-session note. Retirements are recorded here before the complete canonical package is removed, so their version/changelog columns are `N/A`. Write `None` when no spec changed.

| Spec         | Path                               | Change Type        | Spec Version | Prev Version | Changelog Entry      | Change Note                          | Status          |
| ------------ | ---------------------------------- | ------------------ | ------------ | ------------ | -------------------- | ------------------------------------ | --------------- |
| example-spec | specs/example/example-spec/spec.md | created \| updated | 1.1.0        | 1.0.0        | changes/changes.json | changes/{YYYYMMDD}-{session-slug}.md | consolidated    |
| retired-spec | specs/example/retired-spec/        | deleted            | N/A          | N/A          | N/A                  | N/A                                  | package-removed |

## Follow-Ups

Product or project follow-ups for the delivery team (backlog candidates, tech debt, deferred product work) that were not compounded into product docs. Do not record follow-ups that target the SDD framework or its tooling. Write `None` when there are no follow-ups.

| ID         | Type    | Owner | Status | Description                                 |
| ---------- | ------- | ----- | ------ | ------------------------------------------- |
| FOLLOWUP-1 | product | Team  | open   | Deferred product work or backlog candidate. |

## Closure Decision

| Field              | Value    |
| ------------------ | -------- |
| Gate               | retro    |
| Decision           | complete |
| Final topic status | complete |
