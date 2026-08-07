"""ARCHITECTURE.md and AGENTS.md contract validation (behind the validate-*-doc scripts)."""
from __future__ import annotations

import os

from . import contracts, textio
from .cli import Failure


def validate_architecture(architecture_file: str, contract_path: str) -> str:
    if not os.path.isfile(contract_path):
        raise Failure(f"Contract file not found: {contract_path}")
    if not os.path.isfile(architecture_file):
        raise Failure(f"Architecture document not found: {architecture_file}")

    required_sections = contracts.architecture_headings(contract_path)
    if not required_sections:
        raise Failure(f"No required sections found in contract: {contract_path}")

    repo_name = os.path.basename(os.path.dirname(architecture_file))

    if not textio.has_regex(architecture_file, r"^# .+ Architecture[ \t]*$"):
        raise Failure(f"Architecture document must start with a level-1 architecture title: {architecture_file}")

    for section in required_sections:
        if not textio.has_fixed_wholeline(architecture_file, f"## {section}"):
            raise Failure(f"Missing required section '## {section}' in {architecture_file}")

    local = textio.grep_n(architecture_file, textio.LOCAL_PATH_RE.pattern)
    if local:
        raise Failure(local + [f"Architecture document contains an absolute local path: {architecture_file}"])

    bookkeeping = textio.grep_n(
        architecture_file, r"^##[ \t]+(Provenance|Metadata|Cache Metadata|Freshness|Hashes?)[ \t]*$")
    if bookkeeping:
        raise Failure(bookkeeping + [f"Architecture document contains generated bookkeeping metadata: {architecture_file}"])

    return f"Validated {architecture_file} for {repo_name}"


def validate_agents(repo_path: str, contract_path: str) -> str:
    agents_file = os.path.join(repo_path, "AGENTS.md")
    taskfile_yml = os.path.join(repo_path, "Taskfile.yml")
    taskfile_yaml = os.path.join(repo_path, "Taskfile.yaml")

    if not os.path.isfile(contract_path):
        raise Failure(f"Contract file not found: {contract_path}")
    if not os.path.isfile(agents_file):
        raise Failure(f"AGENTS.md not found: {agents_file}")

    if os.path.isfile(taskfile_yml) and os.path.isfile(taskfile_yaml):
        raise Failure(
            f"Both Taskfile.yml and Taskfile.yaml exist; cannot determine a single source "
            f"of truth in {repo_path}")

    taskfile_exists = os.path.isfile(taskfile_yml) or os.path.isfile(taskfile_yaml)

    required = contracts.required_paragraphs(contract_path)
    if not required:
        raise Failure(f"Contract has no required paragraphs: {contract_path}")

    for paragraph in required:
        if not textio.has_fixed_wholeline(agents_file, paragraph):
            raise Failure(f"AGENTS.md is missing required paragraph: {paragraph}")

    taskfile_paragraph = contracts.taskfile_paragraph(contract_path)
    if not taskfile_paragraph:
        raise Failure(f"Contract has no conditional Taskfile paragraph: {contract_path}")

    if taskfile_exists:
        if not textio.has_fixed_wholeline(agents_file, taskfile_paragraph):
            raise Failure(f"AGENTS.md is missing required Taskfile paragraph: {taskfile_paragraph}")
    else:
        if textio.has_fixed_wholeline(agents_file, taskfile_paragraph):
            raise Failure(
                f"AGENTS.md references a repository-root Taskfile, but no Taskfile.yml or "
                f"Taskfile.yaml exists in {repo_path}")

    for literal in contracts.forbidden_literals(contract_path):
        if textio.has_fixed_substr(agents_file, literal):
            raise Failure(f"AGENTS.md contains forbidden literal {literal} in {agents_file}")

    return f"Validated {agents_file}"
