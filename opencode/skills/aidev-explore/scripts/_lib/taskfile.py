"""Taskfile resolution and contract validation (the logic behind validate-taskfile)."""
from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path

import yaml

from . import contracts, repodetect, textio
from .cli import Failure

_SP = r"[ \t]"  # POSIX [[:space:]] within a single line


def resolve_taskfile(repo: str) -> str:
    yml = os.path.join(repo, "Taskfile.yml")
    yaml_ = os.path.join(repo, "Taskfile.yaml")
    if os.path.isfile(yml) and os.path.isfile(yaml_):
        raise Failure(f"Both Taskfile.yml and Taskfile.yaml exist in {repo}")
    if os.path.isfile(yml):
        return yml
    if os.path.isfile(yaml_):
        return yaml_
    raise Failure(f"Taskfile not found in {repo}")


def _parse_tasks(document: dict, taskfile_path: str) -> dict[str, dict]:
    raw_tasks = document.get("tasks")
    if not isinstance(raw_tasks, dict):
        raise Failure(f"Taskfile tasks must be a YAML mapping: {taskfile_path}")
    tasks: dict[str, dict] = {}
    for name, definition in raw_tasks.items():
        if not isinstance(name, str) or not isinstance(definition, dict):
            raise Failure(f"Every Taskfile task must be a named YAML mapping: {taskfile_path}")
        if "cmds" in definition and not isinstance(definition["cmds"], list):
            raise Failure(f"Task '{name}' cmds must be a YAML list in {taskfile_path}")
        if "deps" in definition and not isinstance(definition["deps"], list):
            raise Failure(f"Task '{name}' deps must be a YAML list in {taskfile_path}")
        tasks[name] = definition
    return tasks


def _command_text(entry) -> str:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict) and isinstance(entry.get("cmd"), str):
        return entry["cmd"]
    return ""


def _task_entries(definition: dict) -> list:
    commands = definition.get("cmds", [])
    return commands if isinstance(commands, list) else []


def _task_commands(definition: dict) -> list[str]:
    return [text for entry in _task_entries(definition) if (text := _command_text(entry))]


def _contains_all(definition: dict, patterns: list[str]) -> bool:
    return any(
        all(re.search(pattern, command, re.MULTILINE) is not None for pattern in patterns)
        for command in _task_commands(definition)
    )


def _task_dir(definition: dict) -> str:
    directory = definition.get("dir")
    return directory.strip() if isinstance(directory, str) else ""


def _normalized_task_dir(directory: str) -> str:
    parts = [part for part in directory.split("/") if part not in ("", ".")]
    return "/".join(parts) or "."


def _folder_suffix(directory: str) -> str:
    normalized = _normalized_task_dir(directory)
    if normalized == ".":
        return ""
    folder = normalized.rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "-", folder.lower()).strip("-")


def _base_phase_task_name(phase: str, directory: str) -> str:
    suffix = _folder_suffix(directory)
    return f"{phase}-{suffix}" if suffix else phase


def _validate_directory_task_names(taskfile_path: str, tasks: dict[str, dict]) -> None:
    for name, definition in tasks.items():
        directory = _task_dir(definition)
        if not directory:
            raise Failure(f"Task '{name}' must declare an explicit dir in {taskfile_path}")
        if (directory.startswith(("/", "~")) or "{{" in directory
                or ".." in directory.split("/")):
            raise Failure(
                f"Task '{name}' dir must be a static repository-relative path in {taskfile_path}")
        suffix = _folder_suffix(directory)
        if _normalized_task_dir(directory) != "." and not suffix:
            raise Failure(
                f"Task '{name}' dir basename must normalize to a kebab-case suffix "
                f"in {taskfile_path}")
        if suffix and not name.endswith(f"-{suffix}"):
            raise Failure(
                f"Task '{name}' must end with the affected folder suffix '-{suffix}' "
                f"because its dir is '{directory}' in {taskfile_path}")


def _validate_install_preflights(taskfile_path: str, tasks: dict[str, dict]) -> None:
    for name, definition in tasks.items():
        if name != "install" and not name.startswith("install-"):
            continue
        if definition.get("deps"):
            raise Failure(
                f"Install task '{name}' must not run dependencies before its mandatory "
                f"'asdf install' preflight in {taskfile_path}")
        entries = _task_entries(definition)
        if not entries or _command_text(entries[0]).strip() != "asdf install":
            raise Failure(
                f"Install task '{name}' must use 'asdf install' as its first cmds entry "
                f"in {taskfile_path}")


_SHELL_SEGMENT_RE = re.compile(r"\s*(?:&&|\|\||[;&|]|\n)\s*")


def _shell_tokens(segment: str) -> list[str]:
    try:
        lexer = shlex.shlex(segment, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = "#"
        return list(lexer)
    except ValueError:
        return []


def _host_flag_index(tokens: list[str]) -> int | None:
    for index, token in enumerate(tokens):
        if token == "--host=0.0.0.0":
            return index
        if token == "--host" and index + 1 < len(tokens) and tokens[index + 1] == "0.0.0.0":
            return index
    return None


def _has_host_flag(tokens: list[str]) -> bool:
    return _host_flag_index(tokens) is not None


def _package_script_invocations(segment: str) -> list[tuple[str, str, bool]]:
    tokens = _shell_tokens(segment)
    result: list[tuple[str, str, bool]] = []
    for index, manager in enumerate(tokens):
        if manager not in ("npm", "pnpm", "yarn"):
            continue
        position = index + 1
        while position < len(tokens) and tokens[position].startswith("-"):
            position += 1
        if position < len(tokens) and tokens[position] in ("run", "run-script"):
            position += 1
        if position >= len(tokens) or tokens[position].startswith("-"):
            continue
        script_name = tokens[position]
        trailing = tokens[position + 1:]
        host_index = _host_flag_index(trailing)
        forwarded_host = host_index is not None
        if manager == "npm" and host_index is not None:
            forwarded_host = "--" in trailing[:host_index]
        result.append((manager, script_name, forwarded_host))
    return result


def _direct_frontend_launch(segment: str) -> tuple[bool, bool]:
    tokens = _shell_tokens(segment)
    if not tokens:
        return False, True
    if tokens[0] in ("sh", "bash", "zsh") and len(tokens) >= 3 and tokens[1] == "-c":
        launches, unhosted, _, _ = _analyze_frontend_command(tokens[2], {})
        return launches > 0, unhosted == 0
    position = 0
    while position < len(tokens) and "=" in tokens[position] and not tokens[position].startswith("-"):
        position += 1
    if position < len(tokens) and tokens[position] == "env":
        position += 1
        while position < len(tokens) and "=" in tokens[position] and not tokens[position].startswith("-"):
            position += 1
    if position < len(tokens) and os.path.basename(tokens[position]) in ("cross-env", "cross-env-shell"):
        position += 1
        while position < len(tokens) and "=" in tokens[position] and not tokens[position].startswith("-"):
            position += 1
    if position < len(tokens) and tokens[position] in ("npx", "pnpm", "yarn"):
        position += 1
        if position < len(tokens) and tokens[position] == "exec":
            position += 1
    if position >= len(tokens):
        return False, True
    executable = os.path.basename(tokens[position])
    arguments = tokens[position + 1:]
    if executable == "webpack-dev-server":
        return True, _has_host_flag(arguments)
    if executable == "webpack" and arguments and arguments[0] == "serve":
        return True, _has_host_flag(arguments)
    if executable == "vite" and (not arguments or arguments[0] not in ("build", "optimize")):
        return True, _has_host_flag(arguments)
    return False, True


def _package_scripts(repo_path: str | None, directory: str) -> dict[str, str]:
    if repo_path is None:
        return {}
    package_json = os.path.join(repo_path, directory, "package.json")
    if not os.path.isfile(package_json):
        return {}
    try:
        document = json.loads(Path(package_json).read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = document.get("scripts", {}) if isinstance(document, dict) else {}
    if not isinstance(scripts, dict):
        return {}
    return {str(name): command for name, command in scripts.items() if isinstance(command, str)}


def _analyze_frontend_command(command: str, scripts: dict[str, str],
                              visited: set[str] | None = None,
                              check_redundant: bool = False) -> tuple[int, int, bool, int]:
    launches = 0
    unhosted = 0
    final_unhosted = False
    redundant = 0
    visited = set() if visited is None else visited
    segments = [segment for segment in _SHELL_SEGMENT_RE.split(command) if segment]
    for index, segment in enumerate(segments):
        if not segment:
            continue
        direct_launch, direct_compliant = _direct_frontend_launch(segment)
        if direct_launch:
            launches += 1
            if not direct_compliant:
                unhosted += 1
                final_unhosted = index == len(segments) - 1
        for _, script_name, forwarded_host in _package_script_invocations(segment):
            if script_name in visited or script_name not in scripts:
                continue
            child_launches, child_unhosted, child_forwardable, child_redundant = _analyze_frontend_command(
                scripts[script_name], scripts, visited | {script_name})
            launches += child_launches
            if check_redundant:
                redundant += child_redundant
            if forwarded_host:
                if child_launches and child_unhosted == 0:
                    if check_redundant:
                        redundant += 1
                elif child_unhosted == 1 and child_forwardable:
                    child_unhosted = 0
            if child_unhosted:
                unhosted += child_unhosted
                final_unhosted = False
    return launches, unhosted, unhosted == 1 and final_unhosted, redundant


def _local_task_invocations(command: str, tasks: dict[str, dict]) -> list[str]:
    result = []
    for segment in _SHELL_SEGMENT_RE.split(command):
        tokens = _shell_tokens(segment)
        if tokens and tokens[0] == "task":
            result.extend(token for token in tokens[1:] if not token.startswith("-") and token in tasks)
    return result


def _analyze_frontend_task(name: str, repo_path: str | None, tasks: dict[str, dict],
                           visited: set[str]) -> tuple[bool, bool, bool]:
    if name in visited or name not in tasks:
        return False, True, False
    definition = tasks[name]
    scripts = _package_scripts(repo_path, _task_dir(definition))
    launches = False
    compliant = True
    redundant = False
    for entry in _task_entries(definition):
        command = _command_text(entry)
        if command:
            entry_launches, entry_unhosted, _, entry_redundant = _analyze_frontend_command(
                command, scripts, check_redundant=True)
            entry_compliant = entry_unhosted == 0
            redundant = redundant or entry_redundant > 0
            for delegated_name in _local_task_invocations(command, tasks):
                delegated_launches, delegated_compliant, delegated_redundant = _analyze_frontend_task(
                    delegated_name, repo_path, tasks, visited | {name})
                entry_launches += delegated_launches
                entry_compliant = entry_compliant and delegated_compliant
                redundant = redundant or delegated_redundant
        elif isinstance(entry, dict) and isinstance(entry.get("task"), str):
            entry_launches, entry_compliant, entry_redundant = _analyze_frontend_task(
                entry["task"], repo_path, tasks, visited | {name})
            redundant = redundant or entry_redundant
        else:
            continue
        launches = launches or entry_launches > 0
        compliant = compliant and entry_compliant
    dependencies = definition.get("deps", [])
    if isinstance(dependencies, list):
        for dependency in dependencies:
            if isinstance(dependency, str):
                dependency_name = dependency
            elif isinstance(dependency, dict) and isinstance(dependency.get("task"), str):
                dependency_name = dependency["task"]
            else:
                continue
            dependency_launches, dependency_compliant, dependency_redundant = _analyze_frontend_task(
                dependency_name, repo_path, tasks, visited | {name})
            launches = launches or dependency_launches
            compliant = compliant and dependency_compliant
            redundant = redundant or dependency_redundant
    return launches, compliant, redundant


def _validate_frontend_start_hosts(
        taskfile_path: str, repo_path: str | None, tasks: dict[str, dict]) -> None:
    for name, definition in tasks.items():
        if name != "start" and not name.startswith("start-"):
            continue
        launches, compliant, redundant = _analyze_frontend_task(name, repo_path, tasks, set())
        if launches and not compliant:
            raise Failure(
                f"Frontend start task '{name}' must pass '--host 0.0.0.0' to every "
                f"Vite or Webpack development server in {taskfile_path}")
        if redundant:
            raise Failure(
                f"Frontend start task '{name}' must not forward '--host 0.0.0.0' when "
                f"the immutable underlying package script already supplies it in {taskfile_path}")


def _boot_named_module(pom: str) -> str:
    for module in repodetect._sed_extract(pom, r".*<module>([^<]+)</module>.*"):
        module = module.strip()
        if module and re.search(r"(^|[-_.])boot$", module):
            return module
    return ""


def validate(taskfile_path: str | None, repo_path: str | None, contract_path: str) -> str:
    if taskfile_path is None:
        assert repo_path is not None
        taskfile_path = resolve_taskfile(repo_path)

    if not os.path.isfile(contract_path):
        raise Failure(f"Contract file not found: {contract_path}")
    if not os.path.isfile(taskfile_path):
        raise Failure(f"Taskfile not found: {taskfile_path}")

    try:
        document = yaml.safe_load(Path(taskfile_path).read_text())
    except yaml.YAMLError as exc:
        raise Failure([f"Taskfile is not valid YAML: {taskfile_path}", str(exc)])
    if not isinstance(document, dict):
        raise Failure(f"Taskfile must be a YAML mapping: {taskfile_path}")

    phase_names = contracts.phase_names(contract_path)
    if not phase_names:
        raise Failure(f"Contract has no phase names: {contract_path}")

    if not textio.has_regex(taskfile_path, r"^[ \t]*version:[ \t]*['\"]?3['\"]?[ \t]*$"):
        raise Failure(f"Taskfile must declare version 3: {taskfile_path}")

    if not textio.has_regex(taskfile_path, r"^[ \t]*tasks:[ \t]*$"):
        raise Failure(f"Taskfile is missing the top-level tasks key: {taskfile_path}")

    tasks = _parse_tasks(document, taskfile_path)
    if not tasks:
        raise Failure(f"Taskfile does not define any tasks under the top-level tasks key: {taskfile_path}")

    task_names = list(tasks)

    for name in task_names:
        for phase in phase_names:
            if name.startswith(f"{phase}-"):
                if not re.fullmatch(rf"{phase}-[a-z0-9]+(-[a-z0-9]+)*", name):
                    raise Failure(
                        f"Task '{name}' must use kebab-case variant naming based on "
                        f"the '{phase}' phase in {taskfile_path}")

    _validate_directory_task_names(taskfile_path, tasks)
    _validate_install_preflights(taskfile_path, tasks)
    _validate_frontend_start_hosts(taskfile_path, repo_path, tasks)

    local_path_matches = textio.grep_n(taskfile_path, textio.LOCAL_PATH_RE.pattern)
    if local_path_matches:
        raise Failure(local_path_matches + [f"Taskfile contains an absolute local path: {taskfile_path}"])

    fence_matches = textio.grep_n(taskfile_path, r"^[ \t]*```")
    if fence_matches:
        raise Failure(fence_matches + [f"Taskfile contains Markdown fences: {taskfile_path}"])

    for name in task_names:
        if _contains_all(tasks[name], ["[Nn]o supported command was identified"]):
            raise Failure(
                f"Task '{name}' must be omitted instead of using an unsupported-command "
                f"placeholder: {taskfile_path}")

    if repo_path:
        _validate_repo_policies(taskfile_path, repo_path, phase_names, tasks)

    return f"Validated {taskfile_path}"


def _task_exists(task_names: list[str], name: str) -> bool:
    return name in task_names


def _validate_repo_policies(taskfile_path, repo_path, phase_names, tasks) -> "None":
    task_names = list(tasks)
    detected_build_file, detected_build_system = repodetect.detected_fields(repo_path)
    detected_build_dir = os.path.dirname(detected_build_file) or "."

    diagnostic = (
        r"help:active-profiles|go-offline|dependency:resolve|"
        rf"(^|{_SP})(npm|pnpm|yarn|poetry|uv|go|cargo){_SP}+--version|"
        rf"(^|{_SP})go{_SP}+env|(^|{_SP})cargo{_SP}+metadata"
    )
    for phase in phase_names:
        for task_name in task_names:
            if task_name == phase or task_name.startswith(f"{phase}-"):
                if _contains_all(tasks[task_name], [diagnostic]):
                    raise Failure(
                        f"Task '{task_name}' must not use diagnostic or discovery-only commands "
                        f"as its implementation: {taskfile_path}")

    mvn = rf"(^|{_SP})(\./mvnw|mvnw|mvn)({_SP}|$)"

    if detected_build_system == "Maven" and detected_build_file.endswith("pom.xml"):
        pom_path = os.path.join(repo_path, detected_build_file)
        if os.path.isfile(pom_path):
            install_task = _base_phase_task_name("install", detected_build_dir)
            build_task = _base_phase_task_name("build", detected_build_dir)
            format_task = _base_phase_task_name("format", detected_build_dir)
            test_task = _base_phase_task_name("test", detected_build_dir)
            if _task_exists(task_names, install_task) and not _contains_all(
                    tasks[install_task], [mvn, rf"(^|{_SP})install({_SP}|$)"]):
                raise Failure(
                    f"Maven install task must use the Maven install lifecycle goal when "
                    f"pom.xml is the detected build file: {taskfile_path}")

            if _task_exists(task_names, build_task) and not _contains_all(
                    tasks[build_task],
                    [mvn, rf"(^|{_SP})(clean{_SP}+)?package({_SP}|$)|(^|{_SP})compile({_SP}|$)"]):
                raise Failure(
                    f"Maven build task must use a compile/package lifecycle goal, not install "
                    f"or a diagnostic command: {taskfile_path}")

            if _task_exists(task_names, build_task) and _contains_all(
                    tasks[build_task], [rf"(^|{_SP})install({_SP}|$)"]):
                raise Failure(
                    f"Maven build task must not use install as the base build command: {taskfile_path}")

            if repodetect._matches(
                    pom_path,
                    r"amiga-javaformat-maven-plugin|amiga-javaformat\.version|inditex\.amiga-javaformat\.version"):
                if _task_exists(task_names, format_task) and not _contains_all(
                        tasks[format_task], [mvn, "amiga-javaformat:apply"]):
                    raise Failure(
                        f"Maven format task must use amiga-javaformat:apply when AMIGA Java "
                        f"Format evidence exists: {taskfile_path}")

            if _task_exists(task_names, test_task) and not _contains_all(
                    tasks[test_task], [mvn, rf"(^|{_SP})(test|verify)({_SP}|$)"]):
                raise Failure(
                    f"Maven test task must use a Maven test or verify lifecycle goal: {taskfile_path}")

            boot_module = _boot_named_module(pom_path)
            if boot_module:
                boot_dir = os.path.join(os.path.dirname(detected_build_file), boot_module)
                start_task = _base_phase_task_name("start", boot_dir)
                if _task_exists(task_names, start_task):
                    actual_dir = _normalized_task_dir(_task_dir(tasks[start_task]))
                    if (actual_dir != _normalized_task_dir(boot_dir)
                            or not _contains_all(tasks[start_task], [mvn, "spring-boot:run"])):
                        raise Failure(
                            f"Maven start task must run spring-boot:run from the boot-named module "
                            f"directory '{boot_dir}' when that module is declared: {taskfile_path}")
            elif repodetect._matches(pom_path, r"spring-boot-maven-plugin|<artifactId>[^<]*-boot</artifactId>"):
                start_task = _base_phase_task_name("start", detected_build_dir)
                if _task_exists(task_names, start_task) and not _contains_all(
                        tasks[start_task], [mvn, "spring-boot:run"]):
                    raise Failure(
                        f"Maven start task must use spring-boot:run when runnable Spring Boot "
                        f"evidence exists: {taskfile_path}")

    if detected_build_file.endswith("package.json"):
        package_json_path = os.path.join(repo_path, detected_build_file)
        package_dir = os.path.dirname(package_json_path)
        package_manager = "npm"
        if os.path.isfile(os.path.join(package_dir, "pnpm-lock.yaml")):
            package_manager = "pnpm"
        if os.path.isfile(os.path.join(package_dir, "yarn.lock")):
            package_manager = "yarn"

        for script_phase in ("build", "lint", "format", "test", "start"):
            task_name = _base_phase_task_name(script_phase, detected_build_dir)
            script_exists = (os.path.isfile(package_json_path)
                             and textio.has_regex(package_json_path, rf'"{script_phase}"{_SP}*:'))
            if script_exists and _task_exists(task_names, task_name):
                if not _contains_all(
                        tasks[task_name],
                        [rf"(^|{_SP}){package_manager}({_SP}|$)",
                         rf"run{_SP}+{script_phase}|{package_manager}{_SP}+{script_phase}"]):
                    raise Failure(
                        f"Package task '{script_phase}' must use the explicit package.json "
                        f"script via {package_manager}: {taskfile_path}")
