"""Small parsing and path helpers shared across setup modules."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


GITHUB_ISSUE_RE = re.compile(
    r"^/([^/]+)/([^/]+)/issues/(\d+)(?:/|$)", re.IGNORECASE
)
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
TABLE_SEPARATOR_RE = re.compile(
    r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$"
)


def scalar(value: str) -> str:
    """Read the simple scalar forms used by backlog-plan.yml."""
    value = re.sub(r"\s+#.*$", "", value).strip()
    if value in ("", "null", "~"):
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        try:
            parsed = ast.literal_eval(value)
            return str(parsed)
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def normalise_repo_name(value: str) -> str:
    value = scalar(value).strip().strip("`")
    value = value.removesuffix(".git").rstrip("/")
    return value


def repo_names(value: str) -> list[str]:
    """Return the repositories named by a task's Repo field.

    Plans commonly express cross-repository tasks as ``repo-a and repo-b`` or
    as individually backticked names. Preserve owner/repo slashes while
    accepting those bounded list forms.
    """
    raw = scalar(value).strip()
    quoted = re.findall(r"`([^`]+)`", raw)
    parts = quoted if quoted else re.split(r"\s+(?:and|&)\s+|[,;]", raw)
    result: list[str] = []
    for part in parts:
        name = normalise_repo_name(part)
        if name and name not in result:
            result.append(name)
    return result


def repo_basename(value: str) -> str:
    return normalise_repo_name(value).rsplit("/", 1)[-1]


def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "session"


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("[") and "](" in value and value.endswith(")"):
        value = value[value.find("](") + 2 : -1]
    return value.strip("`").strip()


def split_pipe_row(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [clean_cell(cell) for cell in value.split("|")]


def parse_issue_url(value: str) -> tuple[str, int] | None:
    value = scalar(value).strip().rstrip(")")
    parsed = urlparse(value)
    if parsed.netloc.lower() != "github.com":
        return None
    match = GITHUB_ISSUE_RE.match(parsed.path)
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}", int(match.group(3))


def issue_ref(value: str) -> tuple[str, int] | None:
    value = clean_cell(value)
    parsed = parse_issue_url(value)
    if parsed:
        return parsed
    match = re.search(r"(?:^|#)(\d+)$", value)
    if match:
        return "", int(match.group(1))
    return None


def under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    result: list[tuple[int, int, str]] = []
    fenced = False
    fence_char = ""
    fence_length = 0
    for index, line in enumerate(lines):
        fence = FENCE_RE.match(line)
        if fenced:
            if fence and fence.group(1)[0] == fence_char and len(fence.group(1)) >= fence_length:
                fenced = False
            continue
        if fence:
            fenced = True
            fence_char = fence.group(1)[0]
            fence_length = len(fence.group(1))
            continue
        match = HEADING_RE.match(line)
        if match:
            result.append((index, len(match.group(1)), match.group(2).strip()))
    return result


def without_fenced_lines(lines: Iterable[str]) -> list[str]:
    """Return structural lines while ignoring fenced Markdown content."""
    result: list[str] = []
    fenced = False
    fence_char = ""
    fence_length = 0
    for line in lines:
        fence = FENCE_RE.match(line)
        if fenced:
            if fence and fence.group(1)[0] == fence_char and len(fence.group(1)) >= fence_length:
                fenced = False
            continue
        if fence:
            fenced = True
            fence_char = fence.group(1)[0]
            fence_length = len(fence.group(1))
            continue
        result.append(line)
    return result


def section_bounds(
    lines: list[str],
    heading_list: list[tuple[int, int, str]],
    heading_index: int,
    max_level: int,
) -> tuple[int, int]:
    start = heading_list[heading_index][0]
    end = len(lines)
    for line_index, level, _ in heading_list[heading_index + 1 :]:
        if level <= max_level:
            end = line_index
            break
    return start, end


def find_heading(
    heading_list: list[tuple[int, int, str]], title: str, level: int | None = None
) -> int | None:
    wanted = title.casefold()
    for index, (_, heading_level, heading_title) in enumerate(heading_list):
        if (level is None or heading_level == level) and heading_title.casefold() == wanted:
            return index
    return None


def parse_table(lines: list[str]) -> list[dict[str, str]]:
    rows = [
        split_pipe_row(line)
        for line in without_fenced_lines(lines)
        if line.strip().startswith("|")
    ]
    if len(rows) < 2:
        return []
    header = [cell.casefold() for cell in rows[0]]
    result: list[dict[str, str]] = []
    for row in rows[1:]:
        if TABLE_SEPARATOR_RE.match("|" + "|".join(row) + "|"):
            continue
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        result.append({header[index]: row[index] for index in range(len(header))})
    return result
