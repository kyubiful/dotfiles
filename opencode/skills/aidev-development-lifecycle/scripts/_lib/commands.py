"""Subprocess and temporary-file helpers used by reconciliation modules."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

from .errors import CommandError


DEFAULT_TIMEOUT = 30.0


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    check: bool = True,
) -> str:
    try:
        completed = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CommandError(command, "command not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise CommandError(command, f"command timed out after {timeout:g}s") from exc

    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    if check and completed.returncode != 0:
        raise CommandError(command, f"command exited with {completed.returncode}", output)
    return output.strip()


def json_command(
    command: Sequence[str], *, cwd: Path | None = None, timeout: float = DEFAULT_TIMEOUT
) -> Any:
    output = run_command(command, cwd=cwd, timeout=timeout)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise CommandError(command, "command returned invalid JSON", output) from exc


def write_temp_text(content: str) -> str:
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".md", delete=False
    )
    try:
        handle.write(content)
        return handle.name
    finally:
        handle.close()
