"""Checkpoint hints package.

Public surface is ``emit(command, argv_rest)``; the framework lives in ``core``
and the detector rules in ``rules``. Importing ``rules`` here registers every
detector at package import time, so callers only need ``from .. import
checkpoints`` and ``checkpoints.emit(...)``."""
from __future__ import annotations

from .core import Checkpoint, CheckpointContext, build_context, collect, emit, register
from . import rules as _rules  # noqa: F401  imported for its registration side effects

__all__ = [
    "Checkpoint",
    "CheckpointContext",
    "build_context",
    "collect",
    "emit",
    "register",
]