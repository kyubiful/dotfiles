"""In-process transaction for accepted SDD lifecycle changes."""
from __future__ import annotations

import os
import shutil
import tempfile


def create_candidate_session(session_dir: str) -> str:
    candidate = tempfile.mkdtemp(prefix=".handoff-txn-", dir=session_dir)
    try:
        for name in os.listdir(session_dir):
            if name in ("sdd-state.yml", "trace.md"):
                continue
            if name.startswith((".handoff-txn-", ".handoff-commit-", ".sdd-state-")):
                continue
            source = os.path.join(session_dir, name)
            target = os.path.join(candidate, name)
            if os.path.isdir(source):
                shutil.copytree(source, target, copy_function=os.link, symlinks=True)
            elif os.path.islink(source):
                os.symlink(os.readlink(source), target)
            else:
                os.link(source, target)
        shutil.copy2(
            os.path.join(session_dir, "sdd-state.yml"),
            os.path.join(candidate, "sdd-state.yml"),
        )
        shutil.copy2(
            os.path.join(session_dir, "trace.md"),
            os.path.join(candidate, "trace.md"),
        )
        return candidate
    except BaseException:
        shutil.rmtree(candidate, ignore_errors=True)
        raise


def commit_candidate(
    session_dir: str,
    candidate: str,
    delete_path: str = "",
    delete_paths: tuple[str, ...] = (),
    write_paths: tuple[tuple[str, str], ...] = (),
) -> None:
    """Apply state, trace, request writes, and deletions with in-process rollback."""
    targets = ("sdd-state.yml", "trace.md")
    work = tempfile.mkdtemp(prefix=".handoff-commit-", dir=session_dir)
    backups = {name: os.path.join(work, f"{name}.backup") for name in targets}
    staged = {name: os.path.join(work, f"{name}.new") for name in targets}
    requested_deletes = list(delete_paths)
    if delete_path:
        requested_deletes.append(delete_path)
    requested_deletes = list(dict.fromkeys(requested_deletes))
    delete_backups = [
        (path, os.path.join(work, f"deleted-{index}.backup"))
        for index, path in enumerate(requested_deletes)
        if os.path.lexists(path)
    ]
    write_backups = [
        (destination, source, os.path.join(work, f"written-{index}.backup"))
        for index, (destination, source) in enumerate(write_paths)
    ]
    live_changed = False
    try:
        for name in targets:
            shutil.copy2(os.path.join(session_dir, name), backups[name])
            shutil.copy2(os.path.join(candidate, name), staged[name])
        for original, backup in delete_backups:
            shutil.copy2(original, backup)
        for destination, _source, backup in write_backups:
            if os.path.lexists(destination):
                shutil.copy2(destination, backup)

        for name in targets:
            os.replace(staged[name], os.path.join(session_dir, name))
            live_changed = True

        for original, _backup in delete_backups:
            os.remove(original)
        for destination, source, _backup in write_backups:
            os.replace(source, destination)

    except BaseException:
        if live_changed:
            for name in targets:
                if os.path.isfile(backups[name]):
                    shutil.copy2(backups[name], os.path.join(session_dir, name))
        for original, backup in delete_backups:
            if not os.path.exists(original) and os.path.isfile(backup):
                shutil.copy2(backup, original)
        for destination, _source, backup in write_backups:
            if os.path.isfile(backup):
                shutil.copy2(backup, destination)
            elif os.path.lexists(destination):
                os.remove(destination)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
