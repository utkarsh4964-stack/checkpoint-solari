"""
Filesystem diff engine.

MVP scope per spec: filesystem diffs only, no DOM/network diffing.
Compares two directory snapshots taken as {relative_path: content_hash}
maps and produces a DiffResult.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from backend.models.schemas import DiffResult, FileDiffEntry

MAX_PREVIEW_CHARS = 300


def snapshot_tree(root: Path) -> dict[str, str]:
    """Return {relative_path: sha256(content)} for every file under root."""
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in root.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(root))
            result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _preview(root: Path, rel_path: str) -> str | None:
    full = root / rel_path
    try:
        text = full.read_text(errors="replace")
        return text[:MAX_PREVIEW_CHARS]
    except Exception:
        return None


def diff_trees(before: dict[str, str], after: dict[str, str], root_after: Path) -> DiffResult:
    before_paths = set(before)
    after_paths = set(after)

    added = sorted(after_paths - before_paths)
    removed = sorted(before_paths - after_paths)
    modified = sorted(p for p in (before_paths & after_paths) if before[p] != after[p])

    entries: list[FileDiffEntry] = []
    for path in added:
        entries.append(FileDiffEntry(path=path, change="added", after_preview=_preview(root_after, path)))
    for path in removed:
        entries.append(FileDiffEntry(path=path, change="removed"))
    for path in modified:
        entries.append(FileDiffEntry(path=path, change="modified", after_preview=_preview(root_after, path)))

    return DiffResult(files_added=added, files_removed=removed, files_modified=modified, entries=entries)
