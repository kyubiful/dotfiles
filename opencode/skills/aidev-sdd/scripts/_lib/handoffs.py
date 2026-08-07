"""Minimal reference-based specialist handoff manifests."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import state, text, yamlscan
from .trace import ArtifactRef


DELEGATED_PHASES = {
    "discovery",
    "functional-spec",
    "technical-plan",
    "test-design",
    "implementation",
    "spec-verification",
    "retro",
}

HANDOFF_ASSETS_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "handoffs")
)
PHASE_PROFILES_DIR = os.path.join(HANDOFF_ASSETS_DIR, "phases")

CANONICAL_BASENAMES = {
    "research": "research.md",
    "plan": "plan.md",
    "backlog": "backlog-plan.yml",
    "technical-plan": "tech-plan.md",
    "test-plan": "test-plan.md",
    "code-journal": "code.md",
    "verification": "verification.md",
    "retro": "retro.md",
    "spec": "spec.md",
    "changes-registry": "changes.json",
}

ALLOWED_KINDS = {
    "research",
    "plan",
    "backlog",
    "spec",
    "spec-draft",
    "spec-relations",
    "prototype",
    "technical-plan",
    "test-plan",
    "code-journal",
    "verification",
    "retro",
    "changes-registry",
    "change-note",
}

ALLOWED_ROOT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "artifacts",
    "specs",
    "spec_removals",
    "spec_deletions",
    "contract_mappings",
    "blocker_refs",
}
ALLOWED_ARTIFACT_KEYS = {"kind", "scope", "path"}
ALLOWED_SPEC_KEYS = {"artifact", "relation", "replaces"}
ALLOWED_REPLACEMENT_KEYS = {"scope", "path"}
ALLOWED_SPEC_REMOVAL_KEYS = {"scope", "path"}
ALLOWED_SPEC_DELETION_KEYS = {"registered", "package"}
ALLOWED_SCOPED_PATH_KEYS = {"scope", "path"}
ALLOWED_CONTRACT_MAPPING_KEYS = {"contract", "spec", "acs"}
ALLOWED_BLOCKER_KEYS = {"artifact", "id"}


@dataclass(frozen=True)
class SpecRef:
    artifact: str
    relation: str
    replaces_scope: str = ""
    replaces_path: str = ""


@dataclass(frozen=True)
class SpecRemoval:
    scope: str
    path: str


@dataclass(frozen=True)
class SpecDeletion:
    registered_scope: str
    registered_path: str
    package_path: str
    package_resolved: str


@dataclass(frozen=True)
class ContractMapping:
    contract: str
    spec: str
    acs: tuple[str, ...]


@dataclass(frozen=True)
class HandoffManifest:
    path: str
    phase: str
    status: str
    artifacts: dict[str, ArtifactRef]
    specs: tuple[SpecRef, ...]
    spec_removals: tuple[SpecRemoval, ...]
    spec_deletions: tuple[SpecDeletion, ...]
    contract_mappings: tuple[ContractMapping, ...]
    blocker_refs: tuple[tuple[str, str], ...]


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _reject_unknown(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unsupported fields: {', '.join(unknown)}")


def _current_phase(session_dir: str) -> str:
    lines = text.read_lines(state.state_file_of(session_dir))
    for line in lines:
        if line.startswith("current_phase:"):
            return yamlscan.trim_scalar(line.split(":", 1)[1])
    return ""


def load_phase_profile(phase: str) -> dict[str, Any]:
    if phase not in DELEGATED_PHASES:
        raise ValueError(f"phase is not delegated: {phase}")
    path = os.path.join(PHASE_PROFILES_DIR, f"{phase}.yml")
    if not os.path.isfile(path):
        raise ValueError(f"handoff phase profile not found: {phase}")
    with open(path) as handle:
        profile = yaml.safe_load(handle)
    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        raise ValueError(f"invalid handoff phase profile: {phase}")
    if profile.get("phase") != phase or not isinstance(profile.get("agent"), str):
        raise ValueError(f"handoff phase profile identity is invalid: {phase}")
    artifacts = profile.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError(f"handoff phase profile has no artifacts: {phase}")
    for name, artifact in artifacts.items():
        if not isinstance(name, str) or not isinstance(artifact, dict):
            raise ValueError(f"handoff phase profile artifact is invalid: {phase}:{name}")
        if set(artifact) != ALLOWED_ARTIFACT_KEYS:
            raise ValueError(f"handoff phase profile artifact fields are invalid: {phase}:{name}")
    if not isinstance(profile.get("allowed_flags"), list):
        raise ValueError(f"handoff phase profile has no allowed_flags: {phase}")
    required_command_flags = profile.get("required_command_flags", [])
    if (
        not isinstance(required_command_flags, list)
        or any(not isinstance(flag, str) or not flag for flag in required_command_flags)
    ):
        raise ValueError(f"handoff phase profile required_command_flags are invalid: {phase}")
    return profile


def expected_agent(phase: str) -> str:
    return str(load_phase_profile(phase)["agent"])


def request_path(session_dir: str, phase: str) -> str:
    return os.path.join(session_dir, "handoffs", "requests", f"{phase}.md")


def base_request_path(session_dir: str, phase: str) -> str:
    return os.path.join(session_dir, "handoffs", "requests", f".{phase}.base.md")


def active_request_path(session_dir: str, phase: str) -> str:
    session_root = os.path.realpath(session_dir)
    requests_dir = os.path.join(session_dir, "handoffs", "requests")
    requests_root = os.path.realpath(requests_dir)
    lexical_path = request_path(session_dir, phase)
    resolved = os.path.realpath(lexical_path)
    try:
        root_is_contained = os.path.commonpath((session_root, requests_root)) == session_root
        path_is_contained = os.path.commonpath((requests_root, resolved)) == requests_root
    except ValueError:
        root_is_contained = path_is_contained = False
    if not root_is_contained or not path_is_contained:
        raise ValueError("handoff request path escapes the active session")
    if os.path.islink(lexical_path):
        raise ValueError("handoff request must not be a symlink")
    return lexical_path if os.path.isfile(lexical_path) else ""


def prune_requests_dir(session_dir: str) -> None:
    requests_dir = os.path.join(session_dir, "handoffs", "requests")
    try:
        os.rmdir(requests_dir)
    except OSError:
        pass


def request_cleanup_paths(session_dir: str, phase: str) -> tuple[str, ...]:
    request = active_request_path(session_dir, phase)
    base = base_request_path(session_dir, phase)
    if os.path.islink(base):
        raise ValueError("handoff request base must not be a symlink")
    return tuple(path for path in (request, base if os.path.isfile(base) else "") if path)


def _state_spec_exists(session_dir: str, scope: str, path: str) -> bool:
    records = text.read_lines(state.state_file_of(session_dir))
    return any(
        yamlscan.trim_scalar(current_path) == path
        and (yamlscan.trim_scalar(current_scope) or "session") == scope
        for current_path, current_scope, _relation in yamlscan.parse_state_specs(records)
    )


def _spec_identity(scope: str, path: str) -> tuple[str, ...]:
    parts = Path(path).parts
    try:
        index = parts.index("specs")
    except ValueError as err:
        raise ValueError(f"spec path must be below specs/: {scope}:{path}") from err
    if not parts or parts[-1] != "spec.md" or len(parts[index + 1:-1]) != 2:
        raise ValueError(f"spec path must identify a spec.md package: {scope}:{path}")
    return parts[index + 1:-1]


def _package_identity(path: str) -> tuple[str, ...]:
    parts = Path(path).parts
    try:
        index = parts.index("specs")
    except ValueError as err:
        raise ValueError(f"spec package must be below specs/: {path}") from err
    identity = parts[index + 1:]
    if len(identity) != 2:
        raise ValueError(f"spec package must identify domain and spec name: {path}")
    return identity


def load_manifest(session_dir: str, manifest_path: str) -> HandoffManifest:
    manifest_path = os.path.realpath(manifest_path)
    session_root = os.path.realpath(session_dir)
    handoff_root = os.path.realpath(os.path.join(session_dir, "handoffs"))
    try:
        root_is_contained = os.path.commonpath((session_root, handoff_root)) == session_root
        in_handoff_root = os.path.commonpath((handoff_root, manifest_path)) == handoff_root
    except ValueError:
        root_is_contained = False
        in_handoff_root = False
    if not root_is_contained or not in_handoff_root:
        raise ValueError("handoff manifest must be stored inside the session handoffs/ directory")
    if not os.path.isfile(manifest_path):
        raise ValueError(f"handoff manifest not found: {manifest_path}")
    try:
        with open(manifest_path) as handle:
            raw = yaml.safe_load(handle)
    except yaml.YAMLError as err:
        raise ValueError(f"handoff manifest is not valid YAML: {err}") from err

    root = _mapping(raw, "handoff manifest")
    _reject_unknown(root, ALLOWED_ROOT_KEYS, "handoff manifest")
    if type(root.get("schema_version")) is not int or root.get("schema_version") != 1:
        raise ValueError("handoff manifest must declare schema_version: 1")

    phase = root.get("phase")
    if phase not in DELEGATED_PHASES:
        raise ValueError(f"handoff manifest phase is not delegated: {phase}")
    current = _current_phase(session_dir)
    if phase != current:
        raise ValueError(f"handoff phase must equal current_phase ({current})")

    status = root.get("status")
    if status not in ("ready", "blocked"):
        raise ValueError("handoff status must be ready or blocked")

    artifact_data = _mapping(root.get("artifacts"), "handoff artifacts")
    if not artifact_data:
        raise ValueError("handoff artifacts must not be empty")
    artifacts: dict[str, ArtifactRef] = {}
    for name, value in artifact_data.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            raise ValueError(f"invalid artifact name: {name}")
        item = _mapping(value, f"artifacts.{name}")
        _reject_unknown(item, ALLOWED_ARTIFACT_KEYS, f"artifacts.{name}")
        kind = item.get("kind")
        scope = item.get("scope")
        path = item.get("path")
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"artifacts.{name}.kind is unsupported: {kind}")
        if scope not in ("session", "workspace"):
            raise ValueError(f"artifacts.{name}.scope must be session or workspace")
        if not isinstance(path, str):
            raise ValueError(f"artifacts.{name}.path must be a string")
        resolved = state.resolve_scoped_path(session_dir, scope, path)
        if not os.path.isfile(resolved):
            raise ValueError(f"referenced artifact not found: {scope}:{path}")
        expected = CANONICAL_BASENAMES.get(kind)
        if expected and os.path.basename(path) != expected:
            raise ValueError(f"artifact kind {kind} must use basename {expected}: {path}")
        artifacts[name] = ArtifactRef(name, kind, scope, path, resolved)

    profile = load_phase_profile(phase)
    for name, expected in profile["artifacts"].items():
        expected_kind = expected["kind"]
        if name not in artifacts:
            raise ValueError(f"handoff is missing required artifact for {phase}: {name}")
        if artifacts[name].kind != expected_kind:
            raise ValueError(
                f"artifacts.{name}.kind must be {expected_kind} for {phase}"
            )

    artifact_paths: dict[str, str] = {}
    for name, artifact in artifacts.items():
        if artifact.resolved in artifact_paths:
            raise ValueError(
                f"artifacts {artifact_paths[artifact.resolved]} and {name} "
                "reference the same file"
            )
        artifact_paths[artifact.resolved] = name

    specs: list[SpecRef] = []
    spec_data = root.get("specs", [])
    if not isinstance(spec_data, list):
        raise ValueError("handoff specs must be a list")
    if spec_data and phase not in ("functional-spec", "retro"):
        raise ValueError("spec registry updates are allowed only for functional-spec or retro")
    for index, value in enumerate(spec_data):
        item = _mapping(value, f"specs[{index}]")
        _reject_unknown(item, ALLOWED_SPEC_KEYS, f"specs[{index}]")
        artifact = item.get("artifact")
        relation = item.get("relation")
        if artifact not in artifacts:
            raise ValueError(f"specs[{index}].artifact does not name an artifact: {artifact}")
        if artifacts[artifact].kind != "spec":
            raise ValueError(f"specs[{index}].artifact must reference kind spec")
        if relation not in ("primary", "dependency", "reference"):
            raise ValueError(f"specs[{index}].relation is invalid: {relation}")
        replaces_scope = replaces_path = ""
        if "replaces" in item:
            replacement = _mapping(item["replaces"], f"specs[{index}].replaces")
            _reject_unknown(
                replacement,
                ALLOWED_REPLACEMENT_KEYS,
                f"specs[{index}].replaces",
            )
            replaces_scope = replacement.get("scope")
            replaces_path = replacement.get("path")
            if replaces_scope not in ("session", "workspace"):
                raise ValueError(f"specs[{index}].replaces.scope is invalid")
            if not isinstance(replaces_path, str):
                raise ValueError(f"specs[{index}].replaces.path must be a string")
            state.resolve_scoped_path(session_dir, replaces_scope, replaces_path)
        specs.append(SpecRef(artifact, relation, replaces_scope, replaces_path))

    classified = [spec.artifact for spec in specs]
    if len(classified) != len(set(classified)):
        raise ValueError("handoff specs must classify each artifact at most once")
    unclassified = sorted(
        name
        for name, artifact in artifacts.items()
        if artifact.kind == "spec" and name not in classified
    )
    if unclassified:
        raise ValueError(
            "handoff spec artifacts must be classified in specs: "
            + ", ".join(unclassified)
        )
    if phase == "functional-spec" and not specs:
        raise ValueError("functional-spec handoff must classify at least one spec")
    if phase == "functional-spec" and not any(
        spec.artifact == "primary-spec" and spec.relation == "primary"
        for spec in specs
    ):
        raise ValueError("functional-spec primary-spec must use relation primary")
    if phase == "retro":
        for artifact in artifacts.values():
            if artifact.kind == "spec" and artifact.scope != "workspace":
                raise ValueError("retro canonical specs must use workspace scope")

    spec_removals: list[SpecRemoval] = []
    removal_data = root.get("spec_removals", [])
    if not isinstance(removal_data, list):
        raise ValueError("handoff spec_removals must be a list")
    if removal_data and phase != "functional-spec":
        raise ValueError("spec_removals are allowed only for functional-spec handoffs")
    seen_removals: set[tuple[str, str]] = set()
    replacement_targets = {
        (spec.replaces_scope, spec.replaces_path)
        for spec in specs
        if spec.replaces_path
    }
    classified_targets = {
        (artifacts[spec.artifact].scope, artifacts[spec.artifact].path)
        for spec in specs
    }
    for index, value in enumerate(removal_data):
        item = _mapping(value, f"spec_removals[{index}]")
        _reject_unknown(
            item,
            ALLOWED_SPEC_REMOVAL_KEYS,
            f"spec_removals[{index}]",
        )
        scope = item.get("scope")
        path = item.get("path")
        if scope not in ("session", "workspace"):
            raise ValueError(f"spec_removals[{index}].scope is invalid")
        if not isinstance(path, str):
            raise ValueError(f"spec_removals[{index}].path must be a string")
        state.resolve_scoped_path(session_dir, scope, path)
        identity = (scope, path)
        if identity in seen_removals:
            raise ValueError(f"duplicate spec_removals entry: {scope}:{path}")
        if identity in replacement_targets:
            raise ValueError(f"spec cannot be both removed and replaced: {scope}:{path}")
        if identity in classified_targets:
            raise ValueError(f"spec cannot be both removed and classified: {scope}:{path}")
        seen_removals.add(identity)
        spec_removals.append(SpecRemoval(scope, path))

    spec_deletions: list[SpecDeletion] = []
    deletion_data = root.get("spec_deletions", [])
    if not isinstance(deletion_data, list):
        raise ValueError("handoff spec_deletions must be a list")
    if deletion_data and phase != "retro":
        raise ValueError("spec_deletions are allowed only for retro handoffs")
    seen_deletions: set[tuple[str, str]] = set()
    for index, value in enumerate(deletion_data):
        item = _mapping(value, f"spec_deletions[{index}]")
        _reject_unknown(
            item,
            ALLOWED_SPEC_DELETION_KEYS,
            f"spec_deletions[{index}]",
        )
        registered = _mapping(
            item.get("registered"),
            f"spec_deletions[{index}].registered",
        )
        _reject_unknown(
            registered,
            ALLOWED_SCOPED_PATH_KEYS,
            f"spec_deletions[{index}].registered",
        )
        registered_scope = registered.get("scope")
        registered_path = registered.get("path")
        package_path = item.get("package")
        if registered_scope not in ("session", "workspace"):
            raise ValueError(f"spec_deletions[{index}].registered.scope is invalid")
        if not isinstance(registered_path, str):
            raise ValueError(
                f"spec_deletions[{index}].registered.path must be a string"
            )
        if not isinstance(package_path, str):
            raise ValueError(f"spec_deletions[{index}].package must be a string")
        state.resolve_scoped_path(session_dir, registered_scope, registered_path)
        package_resolved = state.resolve_scoped_path(
            session_dir,
            "workspace",
            package_path,
        )
        if _spec_identity(registered_scope, registered_path) != _package_identity(
            package_path
        ):
            raise ValueError(
                f"spec_deletions[{index}] registered spec and package do not match"
            )
        if not _state_spec_exists(session_dir, registered_scope, registered_path):
            raise ValueError(
                f"spec_deletions[{index}] registered spec is not in session state"
            )
        if os.path.lexists(package_resolved):
            raise ValueError(
                f"spec_deletions[{index}] package must already be absent: {package_path}"
            )
        identity = (registered_scope, registered_path)
        if identity in seen_deletions:
            raise ValueError(
                f"duplicate spec_deletions entry: {registered_scope}:{registered_path}"
            )
        seen_deletions.add(identity)
        spec_deletions.append(
            SpecDeletion(
                registered_scope,
                registered_path,
                package_path,
                package_resolved,
            )
        )

    contract_mappings: list[ContractMapping] = []
    mapping_data = root.get("contract_mappings", [])
    if not isinstance(mapping_data, list):
        raise ValueError("handoff contract_mappings must be a list")
    if mapping_data and phase != "functional-spec":
        raise ValueError(
            "contract_mappings are allowed only for functional-spec handoffs"
        )
    contracts_file = os.path.join(session_dir, "contracts.yml")
    contract_ids: set[str] = set()
    if os.path.isfile(contracts_file):
        contract_ids = {
            yamlscan.trim_scalar(contract_id)
            for contract_id, _path, _sha256 in yamlscan.parse_contract_entries(
                text.read_lines(contracts_file)
            )
            if yamlscan.trim_scalar(contract_id)
        }
    seen_mappings: set[tuple[str, str]] = set()
    mapped_contracts: set[str] = set()
    for index, value in enumerate(mapping_data):
        item = _mapping(value, f"contract_mappings[{index}]")
        _reject_unknown(
            item,
            ALLOWED_CONTRACT_MAPPING_KEYS,
            f"contract_mappings[{index}]",
        )
        contract = item.get("contract")
        spec = item.get("spec")
        acs = item.get("acs")
        if not isinstance(contract, str) or contract not in contract_ids:
            raise ValueError(
                f"contract_mappings[{index}].contract is not in contracts.yml: {contract}"
            )
        if spec not in artifacts or artifacts[spec].kind != "spec":
            raise ValueError(
                f"contract_mappings[{index}].spec must reference a spec artifact"
            )
        if not isinstance(acs, list) or not acs:
            raise ValueError(f"contract_mappings[{index}].acs must not be empty")
        if any(not isinstance(ac, str) or not re.fullmatch(r"AC-[0-9]+", ac) for ac in acs):
            raise ValueError(f"contract_mappings[{index}].acs contains an invalid AC ID")
        if len(acs) != len(set(acs)):
            raise ValueError(f"contract_mappings[{index}].acs contains duplicates")
        available_acs = {
            ac
            for line in text.read_lines(artifacts[spec].resolved)
            for ac in re.findall(r"AC-[0-9]+", line)
        }
        missing_acs = sorted(set(acs) - available_acs)
        if missing_acs:
            raise ValueError(
                f"contract_mappings[{index}] ACs not found in {spec}: "
                + ", ".join(missing_acs)
            )
        identity = (contract, spec)
        if identity in seen_mappings:
            raise ValueError(
                f"duplicate contract_mappings entry: {contract}:{spec}"
            )
        seen_mappings.add(identity)
        mapped_contracts.add(contract)
        contract_mappings.append(ContractMapping(contract, spec, tuple(acs)))
    if phase == "functional-spec" and status == "ready":
        unmapped = sorted(contract_ids - mapped_contracts)
        if unmapped:
            raise ValueError(
                "ready functional-spec handoff is missing contract mappings: "
                + ", ".join(unmapped)
            )

    blockers: list[tuple[str, str]] = []
    blocker_data = root.get("blocker_refs", [])
    if not isinstance(blocker_data, list):
        raise ValueError("handoff blocker_refs must be a list")
    for index, value in enumerate(blocker_data):
        item = _mapping(value, f"blocker_refs[{index}]")
        _reject_unknown(item, ALLOWED_BLOCKER_KEYS, f"blocker_refs[{index}]")
        artifact = item.get("artifact")
        blocker_id = item.get("id")
        if artifact not in artifacts:
            raise ValueError(f"blocker_refs[{index}].artifact is unknown: {artifact}")
        if not isinstance(blocker_id, str) or not blocker_id:
            raise ValueError(f"blocker_refs[{index}].id must be non-empty")
        with open(artifacts[artifact].resolved) as handle:
            artifact_content = handle.read()
        if not re.search(
            rf"(?<![A-Z0-9-]){re.escape(blocker_id)}(?![A-Z0-9-])",
            artifact_content,
        ):
            raise ValueError(
                f"blocker_refs[{index}] id not found in {artifact}: {blocker_id}"
            )
        blockers.append((artifact, blocker_id))
    if status == "blocked" and not blockers:
        raise ValueError("blocked handoff must include at least one blocker_ref")
    if status == "ready" and blockers:
        raise ValueError("ready handoff must not include blocker_refs")

    return HandoffManifest(
        path=os.path.realpath(manifest_path),
        phase=phase,
        status=status,
        artifacts=artifacts,
        specs=tuple(specs),
        spec_removals=tuple(spec_removals),
        spec_deletions=tuple(spec_deletions),
        contract_mappings=tuple(contract_mappings),
        blocker_refs=tuple(blockers),
    )
