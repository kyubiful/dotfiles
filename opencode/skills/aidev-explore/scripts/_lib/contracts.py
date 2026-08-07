"""Parse the aidev-explore reference contracts with PyYAML."""
from __future__ import annotations

from pathlib import Path

import yaml


def _load(contract_path: str) -> dict:
    data = yaml.safe_load(Path(contract_path).read_text())
    return data if isinstance(data, dict) else {}


def phase_names(contract_path: str) -> list[str]:
    data = _load(contract_path)
    return [p["name"] for p in data.get("phases", []) if isinstance(p, dict) and "name" in p]


def required_paragraphs(contract_path: str) -> list[str]:
    data = _load(contract_path)
    items = data.get("required_paragraphs", [])
    return [p["text"] for p in items if isinstance(p, dict) and "text" in p]


def taskfile_paragraph(contract_path: str) -> str:
    data = _load(contract_path)
    conditional = data.get("conditional_paragraphs", {}) or {}
    taskfile = conditional.get("taskfile", {}) or {}
    return taskfile.get("text", "") or ""


def forbidden_literals(contract_path: str) -> list[str]:
    data = _load(contract_path)
    return [str(v) for v in data.get("forbidden_literals", [])]


def architecture_headings(contract_path: str) -> list[str]:
    data = _load(contract_path)
    return [str(sec["heading"]) for sec in data.get("sections", []) if isinstance(sec, dict) and "heading" in sec]
