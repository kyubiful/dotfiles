"""Checkpoint detectors: the actual rules that decide when a hint fires.

Each detector is a pure function that inspects a read-only ``CheckpointContext``
and returns at most one ``Checkpoint``. They are registered with the framework
via ``@register(name, commands)`` and are only evaluated after the commands they
declare interest in. Detectors never mutate state.

This module holds only the rules; the model, registry, context building, and
emission live in ``core.py``. To add a checkpoint, write one detector here and
decorate it with ``@register``."""
from __future__ import annotations

from typing import Optional

from .. import phases
from .core import Checkpoint, CheckpointContext, register

_AUTOPILOT_OFFER_PREFIX = "Autopilot offer after"


def _completed_transition(ctx: CheckpointContext) -> tuple[str, str]:
    """Return the completed phase and its successor for completion commands.

    ``phase-complete`` leaves the completed phase current, while the atomic
    ``accept-handoff`` command advances before checkpoints are evaluated.
    """
    if ctx.current_phase_status == "complete":
        return ctx.current_phase, ctx.next_phase
    if ctx.command == "accept-handoff" and ctx.previous_phase:
        return ctx.previous_phase, ctx.current_phase
    return "", ""


@register("autopilot-offer", commands={"advance", "accept-handoff", "next", "phase-complete", "status"})
def autopilot_offer(ctx: CheckpointContext) -> Optional[Checkpoint]:
    """Offer to switch interactive -> autopilot at the boundary where the last
    user-interaction phase hands off to the autopilot-recommended group.

    Mirrors references/autopilot-offer-checkpoint.md: only in interactive mode,
    only once per session, and never on the `simple` track (whose only
    user-interaction phase is bootstrap, excluded below)."""
    if ctx.execution_mode != "interactive":
        return None
    if ctx.session_status == "complete":
        return None
    if ctx.pending_delegation:
        return None
    # Boundary: we have just entered an autopilot-recommended phase from a
    # planning phase. bootstrap is excluded so the simple track (bootstrap ->
    # implementation) never triggers an offer.
    entered_autopilot_group = ctx.current_phase in phases.AUTOPILOT_PHASES
    came_from_planning = (
        ctx.previous_phase in phases.USER_INTERACTION_PHASES
        and ctx.previous_phase != "bootstrap"
    )
    if not (entered_autopilot_group and came_from_planning):
        return None
    # Never re-offer once an offer outcome was recorded for the session.
    if any(d.startswith(_AUTOPILOT_OFFER_PREFIX) for d in ctx.decisions):
        return None
    return Checkpoint(
        "autopilot-offer",
        f"entering the autopilot-recommended group ({ctx.current_phase}) after "
        f"{ctx.previous_phase} in interactive mode — offer to switch to autopilot "
        "before delegating the next phase, then record the outcome "
        "(references/autopilot-offer-checkpoint.md)",
    )


@register("resume-specialist", commands={"resume-handoff"})
def resume_specialist(ctx: CheckpointContext) -> Optional[Checkpoint]:
    """Favor continuity after a question-blocked handoff resumes."""
    if (
        ctx.session_status == "complete"
        or ctx.pending_delegation
        or ctx.current_phase_status != "in-progress"
    ):
        return None
    return Checkpoint(
        "resume-specialist",
        "continue the original specialist with the resumed request whenever "
        "possible; use a new instance only when it cannot be continued",
    )


@register("phase-boundary", commands={"accept-handoff", "phase-complete"})
def phase_boundary(ctx: CheckpointContext) -> Optional[Checkpoint]:
    """Give mode-aware direction after every non-final phase completes.

    Interactive sessions stop and report before the next phase. Autopilot
    sessions continue, except where the mandatory pre-retro checkpoint takes
    precedence and requires a user decision in both modes.
    """
    if ctx.session_status == "complete":
        return None
    if ctx.pending_delegation:
        return None
    completed_phase, next_phase = _completed_transition(ctx)
    if not completed_phase or not next_phase:
        return None
    if next_phase == "retro":
        return None
    if ctx.execution_mode == "interactive":
        action = (
            f"{completed_phase} is complete — stop and inform the user before "
            f"progressing to {next_phase}"
        )
    elif ctx.execution_mode == "autopilot":
        action = (
            f"{completed_phase} is complete — continue to {next_phase} in "
            "autopilot mode"
        )
    else:
        return None

    action += " \n ensure you give the user a clear summary of the completed phase information and the next phase's objectives, regardless of mode"
    return Checkpoint("phase-boundary", action)


@register("pre-retro-acceptance", commands={"advance", "accept-handoff", "next", "phase-complete", "gate", "status"})
def pre_retro_acceptance(ctx: CheckpointContext) -> Optional[Checkpoint]:
    """Before delegating `retro`, the user must accept the implemented result —
    a mandatory stop even in autopilot (references/pre-retro-acceptance-checkpoint.md)."""
    if ctx.session_status == "complete":
        return None
    if ctx.current_phase != "retro":
        return None
    if ctx.current_phase_status == "complete":
        return None
    return Checkpoint(
        "pre-retro-acceptance",
        "reached retro — stop and get the user's acceptance of the implemented "
        "result before delegating retro, even in autopilot "
        "(references/pre-retro-acceptance-checkpoint.md)",
    )


@register("post-retro-closure", commands={"advance", "accept-handoff", "next", "phase-complete", "status"})
def post_retro_closure(ctx: CheckpointContext) -> Optional[Checkpoint]:
    """After `retro` completes, the user must accept the retro result and confirm
    closing the session before session-complete (references/post-retro-closure-checkpoint.md)."""
    if ctx.session_status == "complete":
        return None
    if ctx.current_phase != "retro" or ctx.current_phase_status != "complete":
        return None
    return Checkpoint(
        "post-retro-closure",
        "retro is complete — stop and get the user's confirmation to close the "
        "session before running session-complete, even in autopilot "
        "(references/post-retro-closure-checkpoint.md)",
    )