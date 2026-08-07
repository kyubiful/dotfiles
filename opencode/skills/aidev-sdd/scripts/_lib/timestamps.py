"""UTC ISO-8601 timestamp validation for the sdd lint/state CLIs."""
from __future__ import annotations

import re

from .lintcore import fail
from .yamlscan import trim_scalar

_ISO_UTC = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$"
)


def validate_current_timestamp_scalar(value: str, field_name: str) -> None:
    if value == "":
        fail(f"{field_name} must be set to a current UTC ISO-8601 timestamp")
    if value == "<AIDEV_NOW_UTC>":
        fail(
            f"{field_name} must replace template placeholder <AIDEV_NOW_UTC> "
            "with a current UTC timestamp"
        )
    if not _ISO_UTC.match(value):
        fail(f"{field_name} must use UTC ISO-8601 format (YYYY-MM-DDTHH:MM:SSZ)")


def validate_decisions_timestamps(lines: list[str]) -> None:
    index = 0
    in_decisions = False
    for line in lines:
        if re.match(r"^decisions:", line):
            in_decisions = True
            continue
        if in_decisions and re.match(r"^\S", line):
            in_decisions = False
        if in_decisions and re.match(r"^\s*-\s+date:", line):
            value = re.sub(r"^\s*-\s+date:\s*", "", line)
            index += 1
            validate_current_timestamp_scalar(
                trim_scalar(value), f"decisions[{index}].date"
            )
