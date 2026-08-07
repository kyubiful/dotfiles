"""Deterministic repository detection — the logic behind detect-repo.

Produces the same JSON (byte layout included) as the original shell script: a pretty-printed
top-level object whose values are compact nested JSON built by `jsonfmt`.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import jsonfmt as J

BUILD_FILE_CANDIDATES = [
    "pom.xml",
    "build.gradle.kts",
    "build.gradle",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
]

_SKIP_DIRS = {"node_modules", "target", "build", "dist", "__pycache__", "vendor"}


def _should_skip_dir(name: str) -> bool:
    return name.startswith(".") or name in _SKIP_DIRS


def _sorted_subdirs(parent: str) -> list[str]:
    try:
        names = sorted(os.listdir(parent))
    except OSError:
        return []
    return [os.path.join(parent, n) for n in names if os.path.isdir(os.path.join(parent, n))]


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return ""


def _matches(path: str, pattern: str) -> bool:
    return re.search(pattern, _read_text(path), re.MULTILINE) is not None


def _sed_extract(path: str, pattern: str) -> list[str]:
    """Per-line greedy single-group extraction, matching `sed -nE 's/.../\\1/p'`."""
    rx = re.compile(pattern)
    out: list[str] = []
    for line in _read_text(path).splitlines():
        m = rx.search(line)
        if m:
            out.append(m.group(1))
    return out


class RepoDetector:
    def __init__(self, repo_path: str):
        self.repo = os.path.abspath(repo_path)
        self.name = os.path.basename(self.repo)

    # --- path helpers ---

    def rel(self, path: str) -> str:
        if path == self.repo:
            return "."
        prefix = self.repo + "/"
        return path[len(prefix):] if path.startswith(prefix) else path

    def rel_dir(self, path: str) -> str:
        rel = self.rel(os.path.dirname(path))
        return rel or "."

    # --- build file discovery ---

    def find_all_build_files(self) -> list[str]:
        out: list[str] = []
        for candidate in BUILD_FILE_CANDIDATES:
            full = os.path.join(self.repo, candidate)
            if os.path.isfile(full):
                out.append(full)
        for subdir in _sorted_subdirs(self.repo):
            if _should_skip_dir(os.path.basename(subdir)):
                continue
            for candidate in BUILD_FILE_CANDIDATES:
                full = os.path.join(subdir, candidate)
                if os.path.isfile(full):
                    out.append(full)
        return out

    def find_first_build_file(self) -> str:
        for candidate in BUILD_FILE_CANDIDATES:
            full = os.path.join(self.repo, candidate)
            if os.path.isfile(full):
                return full
        for subdir in _sorted_subdirs(self.repo):
            if _should_skip_dir(os.path.basename(subdir)):
                continue
            for candidate in BUILD_FILE_CANDIDATES:
                full = os.path.join(subdir, candidate)
                if os.path.isfile(full):
                    return full
        return ""

    # --- classification ---

    def classify_build_file(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        dirpath = os.path.dirname(filepath)
        relative_path = self.rel(filepath)
        stack = "unknown"
        build_system = "unknown"
        amiga = False

        if filename == "pom.xml":
            build_system = "Maven"
            if _matches(filepath, "amiga-framework"):
                stack, amiga = "AMIGA Java", True
            else:
                stack = "generic Java/Maven"
        elif filename in ("build.gradle.kts", "build.gradle"):
            build_system = "Gradle"
            stack = "Java/Gradle"
        elif filename == "pyproject.toml":
            if _matches(filepath, "fwk-amigapython"):
                stack, amiga, build_system = "AMIGA Python", True, "uv"
            else:
                stack = "generic Python"
                if _matches(filepath, r"\[tool\.poetry\]"):
                    build_system = "poetry"
                elif _matches(filepath, r"\[tool\.uv\]") or os.path.isfile(os.path.join(dirpath, "uv.lock")):
                    build_system = "uv"
                else:
                    build_system = "pip"
        elif filename == "package.json":
            if _matches(filepath, "@amiga-fwk-nodejs"):
                stack, amiga = "AMIGA Node", True
            elif _matches(filepath, "@amiga-fwk-web"):
                stack, amiga = "AMIGA Web", True
            else:
                stack = "generic Node.js/Web"
            if os.path.isfile(os.path.join(dirpath, "pnpm-lock.yaml")):
                build_system = "pnpm"
            elif os.path.isfile(os.path.join(dirpath, "yarn.lock")):
                build_system = "yarn"
            else:
                build_system = "npm"
        elif filename == "go.mod":
            build_system = "go"
            if _matches(filepath, "fwk-amigagolang"):
                stack, amiga = "AMIGA Go", True
            else:
                stack = "generic Go"
        elif filename == "Cargo.toml":
            build_system = "cargo"
            if _matches(filepath, "amiga"):
                stack, amiga = "AMIGA Rust", True
            else:
                stack = "generic Rust"

        return J.obj([
            ("build_file", J.s(relative_path)),
            ("stack", J.s(stack)),
            ("build_system", J.s(build_system)),
            ("amiga", J.b(amiga)),
        ])

    # --- boot module ---

    def _boot_named_module(self, pom: str) -> str:
        for module in _sed_extract(pom, r".*<module>([^<]+)</module>.*"):
            module = module.strip()
            if module and re.search(r"(^|[-_.])boot$", module):
                return module
        return ""

    # --- build files inventory ---

    def detect_build_files(self) -> str:
        entries: list[str] = []
        for build_file in self.find_all_build_files():
            entries.append(J.obj([
                ("path", J.s(self.rel(build_file))),
                ("dir", J.s(self.rel_dir(build_file))),
                ("type", J.s(os.path.basename(build_file))),
            ]))
        return J.arr(entries)

    # --- tool versions ---

    def detect_tool_versions(self, build_dir: str) -> str:
        pin = ""
        root_pin = os.path.join(self.repo, ".tool-versions")
        if os.path.isfile(root_pin):
            pin = root_pin
        elif build_dir and build_dir != self.repo and os.path.isfile(os.path.join(build_dir, ".tool-versions")):
            pin = os.path.join(build_dir, ".tool-versions")

        if not pin:
            return "null"

        tools: list[str] = []
        for raw in _read_text(pin).splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split(None, 1)
            tool = parts[0] if parts else ""
            version = parts[1].strip() if len(parts) > 1 else ""
            if not tool or not version:
                continue
            tools.append(f'"{J.esc(tool)}": "{J.esc(version)}"')

        return J.obj([
            ("source", J.s(self.rel(pin))),
            ("tools", "{" + ", ".join(tools) + "}"),
        ])

    # --- maven ---

    def detect_maven_evidence(self) -> str:
        projects: list[str] = []
        for pom in self.find_all_build_files():
            if os.path.basename(pom) != "pom.xml":
                continue
            relative_dir = self.rel_dir(pom)
            modules = J.arr_from_lines(_sed_extract(pom, r".*<module>([^<]+)</module>.*"))
            packaging_all = _sed_extract(pom, r".*<packaging>([^<]+)</packaging>.*")
            packaging = packaging_all[0] if packaging_all else ""
            spring_boot = _matches(pom, r"spring-boot-maven-plugin|org\.springframework\.boot|spring-boot-starter|<artifactId>[^<]*-boot</artifactId>")
            amiga_format = _matches(pom, r"amiga-javaformat-maven-plugin|amiga-javaformat\.version|inditex\.amiga-javaformat\.version")
            validation_plugins = _matches(pom, r"maven-enforcer-plugin|maven-checkstyle-plugin|checkstyle|spotbugs|maven-pmd-plugin|<artifactId>pmd|formatter-maven-plugin|fmt-maven-plugin")
            integration_tests = _matches(pom, r"maven-failsafe-plugin|skipITs|integration-test|src/it|failsafe")

            boot_module = self._boot_named_module(pom)
            if boot_module and relative_dir != ".":
                boot_module = f"{relative_dir}/{boot_module}"

            mvnw = os.path.isfile(os.path.join(os.path.dirname(pom), "mvnw"))

            projects.append(J.obj([
                ("path", J.s(self.rel(pom))),
                ("dir", J.s(relative_dir)),
                ("packaging", J.s(packaging)),
                ("mvnw", J.b(mvnw)),
                ("modules", modules),
                ("capabilities", J.obj([
                    ("spring_boot_runtime", J.b(spring_boot)),
                    ("boot_module", J.s(boot_module)),
                    ("amiga_java_format", J.b(amiga_format)),
                    ("validation_plugins", J.b(validation_plugins)),
                    ("integration_tests", J.b(integration_tests)),
                ])),
            ]))
        return J.obj([("projects", J.arr(projects))])

    # --- node / package managers ---

    @staticmethod
    def _package_manager(directory: str) -> str:
        if os.path.isfile(os.path.join(directory, "pnpm-lock.yaml")):
            return "pnpm"
        if os.path.isfile(os.path.join(directory, "yarn.lock")):
            return "yarn"
        return "npm"

    @staticmethod
    def _package_scripts(package_json: str) -> list[str]:
        try:
            document = json.loads(_read_text(package_json))
        except json.JSONDecodeError:
            return []
        scripts = document.get("scripts", {}) if isinstance(document, dict) else {}
        return [str(name) for name in scripts] if isinstance(scripts, dict) else []

    @staticmethod
    def _package_script_commands(package_json: str) -> str:
        try:
            document = json.loads(_read_text(package_json))
        except json.JSONDecodeError:
            return "{}"
        scripts = document.get("scripts", {}) if isinstance(document, dict) else {}
        if not isinstance(scripts, dict):
            return "{}"
        return "{" + ",".join(
            f"{json.dumps(str(name), ensure_ascii=False)}:"
            f"{json.dumps(command, ensure_ascii=False)}"
            for name, command in scripts.items()
            if isinstance(command, str)
        ) + "}"

    def detect_package_evidence(self) -> str:
        projects: list[str] = []
        for package_json in self.find_all_build_files():
            if os.path.basename(package_json) != "package.json":
                continue
            directory = os.path.dirname(package_json)
            relative_dir = self.rel_dir(package_json)
            manager = self._package_manager(directory)
            scripts = J.arr_from_lines(self._package_scripts(package_json))
            script_commands = self._package_script_commands(package_json)
            lock_lines = []
            if os.path.isfile(os.path.join(directory, "package-lock.json")):
                lock_lines.append(f"{relative_dir}/package-lock.json")
            if os.path.isfile(os.path.join(directory, "pnpm-lock.yaml")):
                lock_lines.append(f"{relative_dir}/pnpm-lock.yaml")
            if os.path.isfile(os.path.join(directory, "yarn.lock")):
                lock_lines.append(f"{relative_dir}/yarn.lock")
            lockfiles = J.arr_from_lines([re.sub(r"^\./", "", x) for x in lock_lines])

            projects.append(J.obj([
                ("path", J.s(self.rel(package_json))),
                ("dir", J.s(relative_dir)),
                ("package_manager", J.s(manager)),
                ("lockfiles", lockfiles),
                ("script_names", scripts),
                ("scripts", script_commands),
            ]))
        return J.obj([("projects", J.arr(projects))])

    # --- python ---

    @staticmethod
    def _toml_section_keys(file: str, section: str) -> list[str]:
        in_section = False
        keys: list[str] = []
        key_re = re.compile(r'^\s*["A-Za-z0-9_.\-]+\s*=')
        for line in _read_text(file).splitlines():
            if line == section:
                in_section = True
                continue
            if in_section and line.startswith("["):
                break
            if in_section and key_re.match(line):
                key = re.sub(r"^\s*", "", line)
                key = re.sub(r"\s*=.*", "", key)
                key = re.sub(r'^"|"$', "", key)
                keys.append(key)
        return keys

    def detect_python_evidence(self) -> str:
        projects: list[str] = []
        for pyproject in self.find_all_build_files():
            if os.path.basename(pyproject) != "pyproject.toml":
                continue
            directory = os.path.dirname(pyproject)
            relative_dir = self.rel_dir(pyproject)
            poetry = _matches(pyproject, r"\[tool\.poetry\]")
            uv = _matches(pyproject, r"\[tool\.uv\]") or os.path.isfile(os.path.join(directory, "uv.lock"))
            ruff = _matches(pyproject, r"\[tool\.ruff\]|\[tool\.ruff\.")
            black = _matches(pyproject, r"\[tool\.black\]")
            mypy = _matches(pyproject, r"\[tool\.mypy\]")
            pytest = _matches(pyproject, r"\[tool\.pytest\.ini_options\]|pytest")

            project_scripts = J.arr_from_lines(self._toml_section_keys(pyproject, "[project.scripts]"))
            poetry_scripts = J.arr_from_lines(self._toml_section_keys(pyproject, "[tool.poetry.scripts]"))
            poe_tasks = J.arr_from_lines(self._toml_section_keys(pyproject, "[tool.poe.tasks]"))
            taskipy_tasks = J.arr_from_lines(self._toml_section_keys(pyproject, "[tool.taskipy.tasks]"))
            lock_lines = []
            if os.path.isfile(os.path.join(directory, "poetry.lock")):
                lock_lines.append(f"{relative_dir}/poetry.lock")
            if os.path.isfile(os.path.join(directory, "uv.lock")):
                lock_lines.append(f"{relative_dir}/uv.lock")
            lockfiles = J.arr_from_lines([re.sub(r"^\./", "", x) for x in lock_lines])

            projects.append(J.obj([
                ("path", J.s(self.rel(pyproject))),
                ("dir", J.s(relative_dir)),
                ("lockfiles", lockfiles),
                ("scripts", J.obj([
                    ("project", project_scripts),
                    ("poetry", poetry_scripts),
                    ("poe_tasks", poe_tasks),
                    ("taskipy_tasks", taskipy_tasks),
                ])),
                ("capabilities", J.obj([
                    ("poetry", J.b(poetry)),
                    ("uv", J.b(uv)),
                    ("ruff", J.b(ruff)),
                    ("black", J.b(black)),
                    ("mypy", J.b(mypy)),
                    ("pytest", J.b(pytest)),
                ])),
            ]))
        return J.obj([("projects", J.arr(projects))])

    # --- go ---

    @staticmethod
    def _make_targets(makefile: str) -> list[str]:
        rx = re.compile(r"^([A-Za-z0-9_.\-]+):([^=]|$).*")
        out: list[str] = []
        for line in _read_text(makefile).splitlines():
            m = rx.match(line)
            if m and not m.group(1).startswith("."):
                out.append(m.group(1))
        return out

    def detect_go_evidence(self) -> str:
        projects: list[str] = []
        for gomod in self.find_all_build_files():
            if os.path.basename(gomod) != "go.mod":
                continue
            base = os.path.dirname(gomod)
            relative_dir = self.rel_dir(gomod)

            makefile_objs: list[str] = []
            for mf in _find_files(base, {"Makefile"}, maxdepth=2):
                makefile_objs.append(J.obj([
                    ("path", J.s(self.rel(mf))),
                    ("targets", J.arr_from_lines(self._make_targets(mf))),
                ]))
            makefiles = J.arr(makefile_objs)

            main_dirs = [self.rel_dir(mf) for mf in _find_files(
                base, {"main.go"}, maxdepth=4,
                path_excludes=("/vendor/", "/target/", "/build/"))]
            main_packages = J.arr_from_lines(main_dirs)

            projects.append(J.obj([
                ("path", J.s(self.rel(gomod))),
                ("dir", J.s(relative_dir)),
                ("makefiles", makefiles),
                ("main_packages", main_packages),
            ]))
        return J.obj([("projects", J.arr(projects))])

    # --- rust ---

    def detect_rust_evidence(self) -> str:
        projects: list[str] = []
        for cargo in self.find_all_build_files():
            if os.path.basename(cargo) != "Cargo.toml":
                continue
            base = os.path.dirname(cargo)
            has_main = os.path.isfile(os.path.join(base, "src", "main.rs"))
            has_bins = _matches(cargo, r"^\[\[bin\]\]")
            workspace = _matches(cargo, r"^\[workspace\]")
            projects.append(J.obj([
                ("path", J.s(self.rel(cargo))),
                ("dir", J.s(self.rel_dir(cargo))),
                ("capabilities", J.obj([
                    ("src_main", J.b(has_main)),
                    ("bin_targets", J.b(has_bins)),
                    ("workspace", J.b(workspace)),
                ])),
            ]))
        return J.obj([("projects", J.arr(projects))])

    # --- compose ---

    @staticmethod
    def _compose_services(compose_file: str) -> list[str]:
        in_services = False
        services: list[str] = []
        for line in _read_text(compose_file).splitlines():
            if re.match(r"^[ \t]*services:[ \t]*$", line):
                in_services = True
                continue
            if in_services and re.match(r"^[^ \t]", line):
                break
            if in_services and re.match(r"^  [A-Za-z0-9_.\-]+:[ \t]*$", line):
                services.append(re.sub(r":.*", "", line.lstrip()))
        return services

    @staticmethod
    def _compose_images(compose_file: str) -> list[str]:
        out: list[str] = []
        for line in _read_text(compose_file).splitlines():
            m = re.match(r"^[ \t]*image:[ \t]*([^#\s].*)$", line)
            if m:
                value = re.sub(r"[ \t]+#.*$", "", m.group(1))
                value = re.sub(r"[ \t]+$", "", value)
                out.append(value)
        return out

    @staticmethod
    def _classify_compose_path(relative_path: str) -> str:
        if ("/src/test/" in relative_path or "/test/" in relative_path
                or "/tests/" in relative_path or "integration" in relative_path):
            return "integration-test"
        if (relative_path.startswith("docker-compose.") or relative_path.startswith("compose.")
                or relative_path.startswith("local/") or relative_path.startswith("docker/")
                or relative_path.startswith("compose/")):
            return "runtime"
        return "auxiliary"

    def _legacy_compose_binary(self) -> bool:
        names = {"Makefile", "package.json", "Taskfile.yml", "Taskfile.yaml"}
        suffixes = (".md", ".yml", ".yaml")
        rx = re.compile(r"(^|[ \t;|&])docker-compose[ \t]+(up|down|run|exec|pull|build|logs|ps|stop|restart)")
        for path in _find_files(
            self.repo, None, maxdepth=5,
            prune_dirs={".git", "node_modules", "target", "build", "dist"},
            name_predicate=lambda n: n in names or n.endswith(suffixes),
        ):
            text = _read_text(path)
            if any(rx.search(line) for line in text.splitlines()):
                return True
        return False

    def detect_compose_evidence(self) -> str:
        legacy = J.b(self._legacy_compose_binary())
        entries: list[str] = []
        compose_names = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
        for compose_file in _find_files(
            self.repo, compose_names,
            path_excludes=("/.git/", "/node_modules/", "/target/", "/build/", "/dist/")):
            relative_path = self.rel(compose_file)
            entries.append(J.obj([
                ("path", J.s(relative_path)),
                ("dir", J.s(self.rel_dir(compose_file))),
                ("classification_hint", J.s(self._classify_compose_path(relative_path))),
                ("services", J.arr_from_lines(self._compose_services(compose_file))),
                ("images", J.arr_from_lines(self._compose_images(compose_file))),
                ("legacy_binary_evidence", legacy),
            ]))
        return J.arr(entries)

    # --- command evidence ---

    def detect_command_evidence(self, build_dir: str) -> str:
        primary = "."
        if build_dir:
            primary = self.rel(build_dir)
        return J.obj([
            ("primary_build_dir", J.s(primary)),
            ("maven", self.detect_maven_evidence()),
            ("package_managers", self.detect_package_evidence()),
            ("python", self.detect_python_evidence()),
            ("go", self.detect_go_evidence()),
            ("rust", self.detect_rust_evidence()),
            ("compose", self.detect_compose_evidence()),
        ])

    # --- assemble ---

    def render(self) -> str:
        build_file = self.find_first_build_file()
        if build_file:
            stack_json = self.classify_build_file(build_file)
            build_dir = os.path.dirname(build_file)
        else:
            stack_json = '{"build_file":"","stack":"unknown","build_system":"unknown","amiga":false}'
            build_dir = ""

        tool_versions = self.detect_tool_versions(build_dir)
        build_files = self.detect_build_files()
        command_evidence = self.detect_command_evidence(build_dir)

        return (
            "{\n"
            f'  "repo_name": "{self.name}",\n'
            f'  "repo_path": "{self.repo}",\n'
            f'  "stack": {stack_json},\n'
            f'  "build_files": {build_files},\n'
            f'  "tool_versions": {tool_versions},\n'
            f'  "command_evidence": {command_evidence}\n'
            "}\n"
        )


def _find_files(root, names, maxdepth=None, prune_dirs=(), path_excludes=(), name_predicate=None):
    root_depth = root.rstrip("/").count(os.sep)
    results: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath.count(os.sep) - root_depth
        dirnames[:] = sorted(d for d in dirnames if d not in prune_dirs)
        if maxdepth is not None and depth >= maxdepth:
            dirnames[:] = []
        for fn in sorted(filenames):
            if maxdepth is not None and depth + 1 > maxdepth:
                continue
            if names is not None and fn not in names:
                continue
            if name_predicate is not None and not name_predicate(fn):
                continue
            full = os.path.join(dirpath, fn)
            if any(exc in full for exc in path_excludes):
                continue
            results.append(full)
    return results


def detect(repo_path: str) -> str:
    return RepoDetector(repo_path).render()


def detected_fields(repo_path: str) -> tuple[str, str]:
    """Return (build_file, build_system) exactly as the shell's sed extraction would."""
    detector = RepoDetector(repo_path)
    build_file = detector.find_first_build_file()
    if not build_file:
        return "", ""
    stack_json = detector.classify_build_file(build_file)
    bf = re.search(r'"build_file":"([^"]*)"', stack_json)
    bs = re.search(r'"build_system":"([^"]*)"', stack_json)
    return (bf.group(1) if bf else ""), (bs.group(1) if bs else "")
