"""Download availability grants for registered files."""

from __future__ import annotations


def normalize_relative_path(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def is_path_granted(relative: str, grants: set[str]) -> bool:
    if not grants:
        return False
    if "" in grants:
        return True
    rel = normalize_relative_path(relative)
    if rel in grants:
        return True
    for grant in grants:
        prefix = normalize_relative_path(grant)
        if prefix and (rel == prefix or rel.startswith(prefix + "/")):
            return True
    return False


def filter_tree_entries(entries: list[dict], grants: set[str]) -> list[dict]:
    return [
        entry
        for entry in entries
        if is_path_granted(str(entry["relative_path"]), grants)
    ]
