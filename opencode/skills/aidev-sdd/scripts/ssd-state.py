#!/usr/bin/env python3
"""sdd-state: session state machine for the AIDevSDD workflow."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib import commands


if __name__ == "__main__":
    raise SystemExit(commands.main(sys.argv[1:]))
