"""Shared file tree nodes and cascade selection helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator
from urllib.parse import urlencode

from pylocalsend.core.file_handler.file_handler import format_size


@dataclass
class FileTreeNode:
    key: str
    name: str
    is_dir: bool
    children: list[FileTreeNode] = field(default_factory=list)
    file_id: str | None = None
    relative_path: str = ""
    raw: dict[str, Any] | None = None


def iter_nodes(node: FileTreeNode) -> Iterator[FileTreeNode]:
    yield node
    for child in node.children:
        yield from iter_nodes(child)


def register_subtree_keys(selected: dict[str, bool], node: FileTreeNode) -> None:
    for item in iter_nodes(node):
        selected.setdefault(item.key, False)


def set_subtree_selected(selected: dict[str, bool], node: FileTreeNode, value: bool) -> None:
    for item in iter_nodes(node):
        selected[item.key] = value


def count_selected(selected: dict[str, bool]) -> int:
    return sum(1 for value in selected.values() if value is True)


def is_node_granted(node: FileTreeNode, grants: set[str]) -> bool:
    from pylocalsend.core.file_handler.download_grants import is_path_granted

    if not grants:
        return False
    if "" in grants:
        return True
    if node.is_dir:
        files = [n for n in iter_nodes(node) if not n.is_dir]
        if not files:
            return is_path_granted(node.relative_path, grants)
        return all(is_path_granted(f.relative_path, grants) for f in files)
    return is_path_granted(node.relative_path, grants)


def apply_grants_to_selected(root: FileTreeNode, grants: set[str], selected: dict[str, bool]) -> None:
    for node in iter_nodes(root):
        selected[node.key] = is_node_granted(node, grants)


def compute_grants(root: FileTreeNode, selected: dict[str, bool]) -> set[str]:
    from pylocalsend.core.file_handler.download_grants import is_path_granted, normalize_relative_path

    nodes = list(iter_nodes(root))
    if nodes and all(selected.get(node.key, False) for node in nodes):
        return {""}

    grants: set[str] = set()
    for node in iter_nodes(root):
        if not selected.get(node.key, False):
            continue
        if node.is_dir:
            subtree = [n for n in iter_nodes(node) if n.key != node.key]
            if subtree and all(selected.get(n.key, False) for n in subtree):
                grants.add(normalize_relative_path(node.relative_path))
            continue
        rel = normalize_relative_path(node.relative_path)
        if not is_path_granted(rel, grants):
            grants.add(rel)
    return grants


def index_nodes(
    roots: list[FileTreeNode],
) -> tuple[dict[str, FileTreeNode], dict[str, str]]:
    by_key: dict[str, FileTreeNode] = {}
    parent_by_key: dict[str, str] = {}

    def walk(node: FileTreeNode, parent: FileTreeNode | None) -> None:
        by_key[node.key] = node
        if parent is not None:
            parent_by_key[node.key] = parent.key
        for child in node.children:
            walk(child, node)

    for root in roots:
        walk(root, None)
    return by_key, parent_by_key


def uncheck_ancestors(
    node: FileTreeNode,
    parent_by_key: dict[str, str],
    nodes_by_key: dict[str, FileTreeNode],
    selected: dict[str, bool],
) -> None:
    parent_key = parent_by_key.get(node.key)
    while parent_key:
        selected[parent_key] = False
        parent_key = parent_by_key.get(parent_key)


def api_item_to_node(item: dict[str, Any]) -> FileTreeNode:
    file_id = str(item["id"])
    return FileTreeNode(
        key=f"root:{file_id}",
        name=str(item["name"]),
        is_dir=bool(item["is_dir"]),
        file_id=file_id,
        relative_path="",
        raw=item,
    )


def local_item_to_node(item: dict[str, Any], *, registered: bool) -> FileTreeNode:
    path = str(item["path"])
    if registered:
        return FileTreeNode(
            key=f"root:{item['id']}",
            name=str(item["name"]),
            is_dir=bool(item["is_dir"]),
            file_id=str(item["id"]),
            relative_path="",
            raw=item,
        )
    return FileTreeNode(
        key=f"path:{path}",
        name=str(item["name"]),
        is_dir=bool(item["is_dir"]),
        relative_path=path,
        raw=item,
    )


def tree_has_sizes(node: FileTreeNode) -> bool:
    for item in iter_nodes(node):
        if item.raw is None or "size" not in item.raw:
            return False
    return True


def tree_entries_to_nodes(root_id: str, root_name: str, entries: list[dict[str, Any]]) -> list[FileTreeNode]:
    root: dict[str, Any] = {"children": {}}
    for entry in entries:
        size = int(entry.get("size", 0))
        parts = str(entry["relative_path"]).split("/")
        current = root["children"]
        current_path = ""
        for part in parts[:-1]:
            current_path = f"{current_path}/{part}" if current_path else part
            node = current.setdefault(
                part,
                {
                    "name": part,
                    "relative_path": current_path,
                    "is_dir": True,
                    "size": 0,
                    "children": {},
                },
            )
            node["size"] += size
            current = node["children"]
        filename = parts[-1]
        current[filename] = {
            "name": filename,
            "relative_path": str(entry["relative_path"]),
            "is_dir": False,
            "size": size,
            "children": {},
        }
    return [_finalize_tree_node(root_id, root_name, node) for node in root["children"].values()]


def _finalize_tree_node(root_id: str, root_name: str, node: dict[str, Any]) -> FileTreeNode:
    relative_path = str(node["relative_path"])
    children = node.get("children", {})
    child_nodes = [_finalize_tree_node(root_id, root_name, child) for child in children.values()]
    size = int(node.get("size", 0))
    is_dir = bool(node["is_dir"])
    raw = {
        "name": str(node["name"]),
        "is_dir": is_dir,
        "size": size,
        "size_human": format_size(size),
        "relative_path": relative_path,
    }
    return FileTreeNode(
        key=f"child:{root_id}:{relative_path}",
        name=str(node["name"]),
        is_dir=is_dir,
        children=child_nodes,
        file_id=root_id,
        relative_path=relative_path,
        raw=raw,
    )


def local_children_to_nodes(
    parent: FileTreeNode,
    children: list[dict[str, Any]],
    *,
    root_base: str | None,
) -> list[FileTreeNode]:
    from pathlib import Path

    base = Path(root_base).resolve() if root_base else None
    nodes: list[FileTreeNode] = []
    for child in children:
        path = str(child["path"])
        if parent.file_id and base is not None:
            relative_path = str(Path(path).resolve().relative_to(base)).replace("\\", "/")
            key = f"child:{parent.file_id}:{relative_path}"
        else:
            relative_path = path
            key = f"path:{path}"
        nodes.append(
            FileTreeNode(
                key=key,
                name=str(child["name"]),
                is_dir=bool(child["is_dir"]),
                file_id=parent.file_id,
                relative_path=relative_path,
                raw=child,
            )
        )
    return nodes


def resolve_browser_download_urls(
    selected: dict[str, bool],
    roots: list[FileTreeNode],
    *,
    token: str | None,
    pin: str | None,
) -> list[str]:
    urls: list[str] = []
    covered_files: set[str] = set()

    for root in roots:
        if not root.is_dir:
            if selected.get(root.key) and root.file_id:
                urls.append(_browser_download_url(root.file_id, "", token=token, pin=pin))
            continue

        if selected.get(root.key):
            urls.append(
                _browser_download_url(
                    root.file_id or "",
                    "",
                    token=token,
                    pin=pin,
                    as_zip=True,
                )
            )
            for node in iter_nodes(root):
                if not node.is_dir:
                    covered_files.add(node.key)
            continue

        for node in iter_nodes(root):
            if node.is_dir or not selected.get(node.key) or node.key in covered_files:
                continue
            if not node.file_id:
                continue
            urls.append(
                _browser_download_url(
                    node.file_id,
                    node.relative_path,
                    token=token,
                    pin=pin,
                )
            )
    return urls


def _browser_download_url(
    file_id: str,
    relative_path: str,
    *,
    token: str | None,
    pin: str | None,
    as_zip: bool = False,
) -> str:
    query: dict[str, str] = {}
    if token:
        query["token"] = token
    elif pin:
        query["pin"] = pin

    if as_zip:
        return f"/api/download/{file_id}/zip?{urlencode(query)}"

    if relative_path:
        query["relative"] = relative_path
    query["browser"] = "1"
    return f"/api/download/{file_id}?{urlencode(query)}"
