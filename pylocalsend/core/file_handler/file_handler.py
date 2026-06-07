"""File metadata and directory traversal (zero-copy — paths only)."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class FileEntry:
    id: str
    path: Path
    name: str
    is_dir: bool
    size: int
    mtime: float


def _dir_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def stat_path(path: Path) -> FileEntry:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    st = path.stat()
    is_dir = path.is_dir()
    size = _dir_size(path) if is_dir else st.st_size
    return FileEntry(
        id=str(uuid.uuid4()),
        path=path,
        name=path.name,
        is_dir=is_dir,
        size=size,
        mtime=st.st_mtime,
    )


def list_dir_contents(path: Path) -> list[dict]:
    path = path.resolve()
    if not path.is_dir():
        raise NotADirectoryError(path)
    items: list[dict] = []
    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        try:
            st = child.stat()
            items.append(
                {
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": _dir_size(child) if child.is_dir() else st.st_size,
                    "mtime": st.st_mtime,
                    "path": str(child),
                }
            )
        except OSError:
            continue
    return items


def iter_files_recursive(root: Path) -> Iterator[tuple[Path, int]]:
    """Yield (absolute path, size) for every file under root."""
    root = root.resolve()
    if root.is_file():
        yield root, root.stat().st_size
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                yield fp, fp.stat().st_size
            except OSError:
                continue


def relative_to_root(file_path: Path, root: Path) -> str:
    return str(file_path.resolve().relative_to(root.resolve())).replace("\\", "/")


def format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024
    return f"{size:.1f} TB"
