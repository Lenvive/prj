"""Bidirectional folder sync between local directories."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SyncEntry:
    relative: str
    size: int
    mtime: float
    checksum: str


def _file_checksum(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while data := f.read(chunk):
            h.update(data)
    return h.hexdigest()


def scan_dir(root: Path) -> dict[str, SyncEntry]:
    root = root.resolve()
    entries: dict[str, SyncEntry] = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            fp = Path(dirpath) / name
            rel = str(fp.relative_to(root)).replace("\\", "/")
            try:
                st = fp.stat()
                entries[rel] = SyncEntry(rel, st.st_size, st.st_mtime, _file_checksum(fp))
            except OSError:
                continue
    return entries


def diff_dirs(local: dict[str, SyncEntry], remote: dict[str, SyncEntry]) -> tuple[list[str], list[str], list[str]]:
    """Return (only_local, only_remote, conflict) relative paths."""
    local_keys = set(local)
    remote_keys = set(remote)
    only_local = sorted(local_keys - remote_keys)
    only_remote = sorted(remote_keys - local_keys)
    conflict = sorted(
        k for k in local_keys & remote_keys
        if local[k].checksum != remote[k].checksum
    )
    return only_local, only_remote, conflict


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as fin, dest.open("wb") as fout:
        while chunk := fin.read(1024 * 1024):
            fout.write(chunk)


def sync_to_remote(local_root: Path, remote_root: Path) -> list[str]:
    """Copy newer/missing local files to remote folder (simple mirror push)."""
    local = scan_dir(local_root)
    remote = scan_dir(remote_root)
    copied: list[str] = []
    for rel, entry in local.items():
        dest = remote_root / rel
        if rel not in remote or remote[rel].checksum != entry.checksum:
            copy_file(local_root / rel, dest)
            copied.append(rel)
    return copied


def sync_from_remote(remote_root: Path, local_root: Path) -> list[str]:
    """Copy newer/missing remote files to local folder (simple mirror pull)."""
    return sync_to_remote(remote_root, local_root)
