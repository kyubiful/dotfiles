"""Data models shared by lifecycle setup modules."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BacklogCandidate:
    backlog_id: str
    issue_url: str
    issue_number: int
    repo: str
    source: str


@dataclass
class Task:
    task_id: str
    title: str
    repo: str
    module: str
    backlog_item: str
    dependencies: list[str]
    where: str
    details: str
    exit_criteria: list[str]
    markdown: str
    start_line: int
    end_line: int


@dataclass
class Gate:
    repo: str
    task_refs: list[str]
    checks: list[str]
    start_line: int
    end_line: int


@dataclass
class ExecutionPhase:
    phase: str
    task_refs: list[str]
    notes: str


@dataclass
class TechPlan:
    path: str
    title: str
    tasks: list[Task]
    gates: list[Gate]
    execution_order: list[ExecutionPhase]
    critical_path: str
    parallelizable: str
    backlog_candidates: list[BacklogCandidate]


@dataclass
class ParentResolution:
    status: str
    candidate: BacklogCandidate | None = None
    candidates: list[BacklogCandidate] = field(default_factory=list)
    unpublished_items: list[str] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)


@dataclass
class ExistingArtifacts:
    issue: str = ""
    branch: str = ""
    pr: str = ""
    github_repo: str = ""


@dataclass
class RepoContext:
    target_repo: str
    local_path: str = ""
    github_repo: str = ""
    current_branch: str = ""
    dirty: bool = False
    blockers: list[str] = field(default_factory=list)
    existing: ExistingArtifacts = field(default_factory=ExistingArtifacts)


@dataclass
class RepoPlan:
    context: RepoContext
    tasks: list[Task]
    gates: list[Gate]
    issue_title: str
    issue_body: str
    kind_label: str
    blockers: list[str] = field(default_factory=list)


@dataclass
class RepoOutcome:
    target_repo: str
    local_path: str = ""
    github_repo: str = ""
    branch: str = "n/a"
    issue_url: str = "n/a"
    issue_number: int | None = None
    pr_url: str = "n/a"
    status: str = "blocked"
    issue_status: str = "blocked"
    branch_status: str = "blocked"
    pr_status: str = "blocked"
    selected_kind_label: str = "n/a"
    label_note: str = "none"
    backlog_id: str = "n/a"
    parent_issue: str = "n/a"
    link_type: str = "n/a"
    backlog_link_status: str = "n/a"
    backlog_link_notes: str = "none"
    blockers: list[str] = field(default_factory=list)


@dataclass
class JournalData:
    repositories: dict[str, ExistingArtifacts] = field(default_factory=dict)
    task_rows: dict[str, dict[str, str]] = field(default_factory=dict)
    phase_rows: dict[str, dict[str, str]] = field(default_factory=dict)
    overall_status: str = ""
