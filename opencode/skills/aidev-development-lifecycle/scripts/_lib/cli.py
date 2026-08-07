"""Command-line parser and executable entry point."""
from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from .commands import DEFAULT_TIMEOUT
from .errors import SetupError
from .orchestration import run_apply, run_inspect


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tech-plan", required=True, help="path to the Markdown tech plan")
    parser.add_argument(
        "--workspace",
        default=os.getcwd(),
        help="workspace root; repository discovery is bounded to this directory",
    )
    parser.add_argument(
        "--session-path",
        help=(
            "explicitly trusted framework session containing backlog-plan.yml and code.md; "
            "it is independent of the repository workspace"
        ),
    )
    parser.add_argument(
        "--backlog-plan",
        help="explicit backlog-plan.yml path; defaults to <session-path>/backlog-plan.yml",
    )
    parser.add_argument(
        "--delivery-mode",
        required=True,
        choices=("github-delivery", "local-only"),
        help="explicitly select GitHub artifact delivery or local-only grounding",
    )
    parser.add_argument(
        "--kind-label",
        action="append",
        default=[],
        metavar="REPO=kind/LABEL",
        help="technical issue label mapping; repeat per repository or provide one global label",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"subprocess timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "text"),
        default="json",
        help="output format (default: json)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or apply deterministic Phase 1 delivery setup from a tech plan."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser(
        "inspect", help="parse and inspect without mutating GitHub, git, or the journal"
    )
    _add_common_arguments(inspect_parser)
    inspect_parser.set_defaults(handler=run_inspect)

    apply_parser = subparsers.add_parser(
        "apply", help="reconcile GitHub, git, and the Phase 1 journal"
    )
    _add_common_arguments(apply_parser)
    apply_parser.add_argument(
        "--confirm",
        action="store_true",
        help="confirm that this invocation may mutate GitHub, git, and code.md",
    )
    apply_parser.set_defaults(handler=run_apply)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except SetupError as exc:
        print(f"setup.py: {exc}", file=sys.stderr)
        return 2
