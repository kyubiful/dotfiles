#!/usr/bin/env python3
"""Apply one verified lifecycle journal checkpoint from a JSON payload."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _lib.errors import SetupError  # noqa: E402
from _lib.journal import apply_journal_checkpoint  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply a verified Task Progress and Phase Status checkpoint."
    )
    parser.add_argument("--session-path", required=True, help="framework session containing code.md")
    parser.add_argument("--payload", required=True, help="JSON file with checkpoint updates")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = Path(args.session_path).expanduser().resolve()
    payload_path = Path(args.payload).expanduser().resolve()
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"journal_checkpoint.py: cannot read payload: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"journal_checkpoint.py: invalid JSON payload: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("journal_checkpoint.py: payload must be a JSON object", file=sys.stderr)
        return 2
    try:
        journal = apply_journal_checkpoint(session / "code.md", payload)
    except SetupError as exc:
        print(f"journal_checkpoint.py: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "journal_path": str(session / "code.md"),
                "overall_status": journal.overall_status,
                "phase": payload["phase_update"]["phase"],
                "phase_status": payload["phase_update"]["status"],
                "updated_tasks": [update["task_id"] for update in payload.get("task_updates", [])],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
