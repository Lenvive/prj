"""Receiver WebUI — browse and download with progress."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nicegui import ui

from pylocalsend.core.receiver.receiver import ReceiverClient
from pylocalsend.core.transfer.server_entry import get_service
from pylocalsend.core.utils.config import AppConfig

STYLE = """
<style>
    body { background: #fafafa; color: #333; font-family: "Segoe UI", "Helvetica Neue", sans-serif; }
    .q-card { box-shadow: none !important; border: 1px solid #e8e8e8; border-radius: 2px; }
    .page-title { font-weight: 300; letter-spacing: 0.08em; font-size: 1.4rem; color: #222; }
    .muted { color: #888; font-size: 0.85rem; }
    .file-tree {
        width: 1180px;
        max-width: 100%;
        overflow-x: auto;
        border: 1px solid #e8e8e8;
        border-radius: 2px;
        background: #fff;
    }
    .file-toolbar {
        width: 1180px;
        max-width: 100%;
        padding: 12px;
        border: 1px solid #e8e8e8;
        border-radius: 2px;
        background: #fff;
    }
    .file-row {
        display: grid;
        grid-template-columns: 260px 90px 110px 320px 160px 186px;
        gap: 12px;
        align-items: center;
        box-sizing: border-box;
        width: 1180px;
        min-height: 44px;
        padding: 8px 12px;
        border-bottom: 1px solid #f0f0f0;
    }
    .file-row:last-child { border-bottom: none; }
    .file-row-head { min-height: 36px; color: #888; font-size: 0.78rem; background: #fcfcfc; }
    .file-cell { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .file-name-cell { display: flex; align-items: center; gap: 6px; min-width: 0; }
    .file-name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .expand-spacer { width: 28px; min-width: 28px; }
    .tree-note { color: #aaa; font-size: 0.82rem; padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
    .progress-panel {
        width: 1180px;
        max-width: 100%;
        max-height: 260px;
        overflow-y: auto;
        padding: 12px;
        border: 1px solid #e8e8e8;
        border-radius: 2px;
        background: #fff;
    }
    .progress-item {
        padding: 10px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .progress-item:last-child { border-bottom: none; }
    .progress-meta {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 6px;
        font-size: 0.85rem;
    }
    .progress-name {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        color: #333;
    }
    .progress-percent {
        min-width: 52px;
        text-align: right;
        color: #666;
        font-variant-numeric: tabular-nums;
    }
</style>
"""


def build_receiver_page(token: str | None = None, host: str | None = None, pin: str | None = None) -> None:
    ui.add_head_html(STYLE)
    cfg = AppConfig.load()

    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-6"):
        if token:
            svc = get_service()
            receiver = svc.db.get_receiver_by_token(token)
            if not receiver:
                ui.label("无效链接").classes("text-negative")
                return
            pin = receiver["pin"]
            host = svc.base_url
            client = ReceiverClient(host, pin, token=token, max_parallel=cfg.max_parallel)
            ui.label(f"接收端 · {receiver['name']}").classes("page-title")
        else:
            if not host or not pin:
                ui.label("需要 host 与 PIN").classes("text-negative")
                return
            client = ReceiverClient(host, pin, max_parallel=cfg.max_parallel)
            ui.label("接收端").classes("page-title")

        ui.label(f"Sender · {host}").classes("muted")

        file_list = ui.column().classes("w-full gap-3")
        selected: dict[str, bool] = {}
        expanded: set[str] = set()
        current_files: list[dict[str, Any]] = []

        dest_input = ui.input(
            "下载目录（绝对路径）",
            value=str(Path.home() / "Downloads"),
        ).classes("w-full").props("outlined dense")
        with ui.element("div").classes("file-toolbar"):
            with ui.row().classes("w-full items-center justify-between gap-3"):
                selected_label = ui.label("已选择 0 项").classes("muted")
                with ui.row().classes("gap-2"):
                    ui.button("全选", on_click=lambda _e: select_all()).props("flat dense")
                    ui.button("清空选择", on_click=lambda _e: clear_selection()).props("flat dense")
                    download_btn = ui.button("下载已选").props("unelevated color=primary dense")

        def update_selection_summary() -> None:
            count = sum(1 for value in selected.values() if value)
            selected_label.text = f"已选择 {count} 项"
            if count:
                download_btn.enable()
            else:
                download_btn.disable()

        async def select_all() -> None:
            for f in current_files:
                selected[str(f["id"])] = True
            update_selection_summary()
            await load_files()
            ui.notify("已选择全部顶层项目", type="positive")

        async def clear_selection() -> None:
            for fid in list(selected):
                selected[fid] = False
            update_selection_summary()
            await load_files()
            ui.notify("已清空选择", type="info")

        async def load_files() -> None:
            file_list.clear()
            try:
                files = await client.list_files()
            except Exception as ex:
                with file_list:
                    ui.label(f"无法加载文件列表：{ex}").classes("text-negative")
                return

            current_files.clear()
            current_files.extend(files)
            for f in files:
                selected.setdefault(str(f["id"]), False)
            selected_keys = {str(f["id"]) for f in files}
            for fid in list(selected):
                if fid not in selected_keys:
                    selected.pop(fid)
            update_selection_summary()

            with file_list:
                if not files:
                    ui.label("暂无可下载文件。").classes("muted")
                    return

                with ui.element("div").classes("file-tree w-full"):
                    _render_file_header()
                    for f in files:
                        await _render_remote_node(
                            client,
                            f,
                            selected,
                            expanded,
                            load_files,
                            update_selection_summary,
                        )

        async def do_download() -> None:
            ids = [fid for fid, on in selected.items() if on]
            if not ids:
                ui.notify("请选择文件", type="warning")
                return
            dest = Path(dest_input.value.strip())
            progress_area.clear()
            bars: dict[str, Any] = {}
            with progress_area:
                ui.label("下载进度").classes("muted")

            def on_progress(label: str, done: int, total: int) -> None:
                if label not in bars:
                    with progress_area:
                        with ui.element("div").classes("progress-item"):
                            with ui.element("div").classes("progress-meta"):
                                ui.label(label).classes("progress-name")
                                percent_label = ui.label("0%").classes("progress-percent")
                            bar = ui.linear_progress(value=0, show_value=False).classes("w-full")
                    bars[label] = {"bar": bar, "percent": percent_label}
                ratio = min(1.0, max(0.0, done / total)) if total else 0
                bars[label]["bar"].value = ratio
                bars[label]["percent"].text = f"{ratio * 100:.1f}%"

            try:
                await client.download_items(ids, dest, progress_callback=on_progress)
                ui.notify("下载完成", type="positive")
            except Exception as ex:
                ui.notify(str(ex), type="negative")

        async def start_download(_e: Any = None) -> None:
            await do_download()

        download_btn.on("click", start_download)
        update_selection_summary()

        with ui.row().classes("gap-2"):
            ui.button("刷新列表", on_click=load_files).props("flat")
        progress_area = ui.column().classes("progress-panel")
        with progress_area:
            ui.label("等待下载任务...").classes("muted")
        ui.timer(0.1, load_files, once=True)


def _render_file_header() -> None:
    with ui.element("div").classes("file-row file-row-head"):
        ui.label("名称").classes("file-cell")
        ui.label("类型").classes("file-cell")
        ui.label("大小").classes("file-cell")
        ui.label("位置").classes("file-cell")
        ui.label("时间").classes("file-cell")
        ui.label("操作").classes("file-cell")


async def _render_remote_node(
    client: ReceiverClient,
    item: dict[str, Any],
    selected: dict[str, bool],
    expanded: set[str],
    refresh: Any,
    update_selection_summary: Any,
    *,
    depth: int = 0,
    parent_name: str | None = None,
) -> None:
    is_dir = bool(item["is_dir"])
    fid = str(item["id"])
    expanded_key = _node_key(item)
    is_expanded = expanded_key in expanded

    async def toggle() -> None:
        if expanded_key in expanded:
            expanded.remove(expanded_key)
        else:
            expanded.add(expanded_key)
        await refresh()

    with ui.element("div").classes("file-row"):
        with ui.element("div").classes("file-cell file-name-cell").style(f"padding-left: {depth * 22}px"):
            if is_dir:
                ui.button("−" if is_expanded else "+", on_click=toggle).props("flat dense round").classes("text-grey-7")
            else:
                ui.element("span").classes("expand-spacer")
            ui.icon("folder" if is_dir else "insert_drive_file").classes("text-grey-7")
            ui.label(str(item["name"])).classes("file-name-text")
        ui.label("文件夹" if is_dir else "文件").classes("file-cell muted")
        ui.label(_size_text(item)).classes("file-cell muted")
        ui.label(_location_text(item, parent_name)).classes("file-cell muted")
        ui.label(_time_text(item)).classes("file-cell muted")
        with ui.row().classes("gap-1"):
            if depth == 0:
                select_button = ui.button(
                    "取消选择" if selected.get(fid, False) else "选择下载",
                ).props("flat dense")
                select_button.on(
                    "click",
                    lambda _e, file_id=fid, button=select_button: _toggle_selected(
                        selected,
                        file_id,
                        update_selection_summary,
                        button,
                    ),
                )
            ui.button("详情", on_click=lambda _e, node=dict(item): _show_details(node)).props("flat dense")

    if is_dir and is_expanded:
        try:
            tree = await client.get_tree(fid)
        except Exception as ex:
            ui.label(f"无法读取目录：{ex}").classes("tree-note").style(f"padding-left: {depth * 22 + 46}px")
            return
        children = _tree_entries_to_nodes(str(item["name"]), tree)
        if not children:
            ui.label("空文件夹").classes("tree-note").style(f"padding-left: {depth * 22 + 46}px")
            return
        for child in children:
            _render_tree_node(child, expanded, refresh, depth=depth + 1)


def _render_tree_node(
    item: dict[str, Any],
    expanded: set[str],
    refresh: Any,
    *,
    depth: int,
) -> None:
    is_dir = bool(item["is_dir"])
    key = _node_key(item)
    is_expanded = key in expanded

    async def toggle() -> None:
        if key in expanded:
            expanded.remove(key)
        else:
            expanded.add(key)
        await refresh()

    with ui.element("div").classes("file-row"):
        with ui.element("div").classes("file-cell file-name-cell").style(f"padding-left: {depth * 22}px"):
            if is_dir:
                ui.button("−" if is_expanded else "+", on_click=toggle).props("flat dense round").classes("text-grey-7")
            else:
                ui.element("span").classes("expand-spacer")
            ui.icon("folder" if is_dir else "insert_drive_file").classes("text-grey-7")
            ui.label(str(item["name"])).classes("file-name-text")
        ui.label("文件夹" if is_dir else "文件").classes("file-cell muted")
        ui.label(_size_text(item)).classes("file-cell muted")
        ui.label(str(item["path"])).classes("file-cell muted")
        ui.label("-").classes("file-cell muted")
        ui.button("详情", on_click=lambda _e, node=dict(item): _show_details(node)).props("flat dense")

    if is_dir and is_expanded:
        children = item.get("children", [])
        if not children:
            ui.label("空文件夹").classes("tree-note").style(f"padding-left: {depth * 22 + 46}px")
            return
        for child in children:
            _render_tree_node(child, expanded, refresh, depth=depth + 1)


def _tree_entries_to_nodes(root_name: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root: dict[str, Any] = {"children": {}}
    for entry in entries:
        parts = str(entry["relative_path"]).split("/")
        current = root["children"]
        current_path = root_name
        for part in parts[:-1]:
            current_path = f"{current_path}/{part}"
            node = current.setdefault(
                part,
                {
                    "name": part,
                    "path": current_path,
                    "is_dir": True,
                    "size": 0,
                    "children": {},
                },
            )
            node["size"] += int(entry.get("size", 0))
            current = node["children"]
        filename = parts[-1]
        current[filename] = {
            "name": filename,
            "path": str(entry["relative_path"]),
            "is_dir": False,
            "size": int(entry.get("size", 0)),
            "children": {},
        }
    return [_finalize_tree_node(node) for node in root["children"].values()]


def _finalize_tree_node(node: dict[str, Any]) -> dict[str, Any]:
    children = node.get("children", {})
    node["children"] = [_finalize_tree_node(child) for child in children.values()]
    return node


def _node_key(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("path") or item["name"])


def _toggle_selected(
    selected: dict[str, bool],
    file_id: str,
    update_selection_summary: Any,
    button: Any,
) -> None:
    selected[file_id] = not selected.get(file_id, False)
    button.text = "取消选择" if selected[file_id] else "选择下载"
    update_selection_summary()


def _size_text(item: dict[str, Any]) -> str:
    if "size_human" in item:
        return str(item["size_human"])
    return f"{int(item.get('size', 0))} B"


def _location_text(item: dict[str, Any], parent_name: str | None) -> str:
    if "path" in item:
        return str(item["path"])
    return parent_name or "-"


def _time_text(item: dict[str, Any]) -> str:
    return str(item.get("uploaded_at") or item.get("status") or "-")


def _show_details(item: dict[str, Any]) -> None:
    details = [
        ("名称", item["name"]),
        ("类型", "文件夹" if item["is_dir"] else "文件"),
        ("大小", _size_text(item)),
        ("位置", item.get("path", "-")),
        ("时间", _time_text(item)),
    ]
    if "id" in item:
        details.append(("ID", item["id"]))
    if "status" in item:
        details.append(("状态", item["status"]))

    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96 max-w-3xl"):
        ui.label("文件详情").classes("page-title mb-4")
        for label, value in details:
            with ui.row().classes("w-full items-start gap-3"):
                ui.label(f"{label}:").classes("muted").style("width: 64px; min-width: 64px;")
                ui.label(str(value)).classes("text-sm break-all")
        ui.button("关闭", on_click=dlg.close).props("flat")
    dlg.open()
