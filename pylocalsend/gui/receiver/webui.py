"""Receiver WebUI — browse and download with progress."""

from __future__ import annotations

import json
from typing import Any

from nicegui import ui
from nicegui.events import UploadEventArguments, ValueChangeEventArguments

from pylocalsend.core.receiver.receiver import ReceiverClient
from pylocalsend.core.transfer.server_entry import get_service
from pylocalsend.core.utils.config import AppConfig
from pylocalsend.core.file_handler.file_handler import format_size
from pylocalsend.gui.file_tree import (
    FileTreeNode,
    api_item_to_node,
    count_selected,
    index_nodes,
    iter_nodes,
    register_subtree_keys,
    resolve_browser_download_urls,
    set_subtree_selected,
    tree_entries_to_nodes,
    tree_has_sizes,
    uncheck_ancestors,
)

STYLE = """
<style>
    body { background: #fafafa; color: #333; font-family: "Segoe UI", "Helvetica Neue", sans-serif; }
    .q-card { box-shadow: none !important; border: 1px solid #e8e8e8; border-radius: 2px; }
    .page-title { font-weight: 300; letter-spacing: 0.08em; font-size: 1.4rem; color: #222; }
    .muted { color: #888; font-size: 0.85rem; }
    .file-tree {
        width: min(1360px, 100%);
        margin-inline: auto;
        overflow-x: auto;
        border: 1px solid #e8e8e8;
        border-radius: 2px;
        background: #fff;
    }
    .file-toolbar {
        width: min(1360px, 100%);
        margin-inline: auto;
        padding: 12px 16px;
        border: 1px solid #e8e8e8;
        border-radius: 2px;
        background: #fff;
    }
    .file-row {
        display: grid;
        grid-template-columns: 40px minmax(240px, 1.2fr) 90px 110px minmax(280px, 1fr) 160px 120px;
        gap: 16px;
        align-items: center;
        box-sizing: border-box;
        width: 100%;
        min-width: 1040px;
        min-height: 44px;
        padding: 8px 16px;
        border-bottom: 1px solid #f0f0f0;
    }
    .file-row:last-child { border-bottom: none; }
    .file-row-head { min-height: 36px; color: #888; font-size: 0.78rem; background: #fcfcfc; }
    .file-cell { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .select-cell { display: flex; align-items: center; justify-content: center; }
    .file-name-cell { display: flex; align-items: center; gap: 6px; min-width: 0; }
    .file-name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .expand-spacer { width: 28px; min-width: 28px; }
    .tree-note { color: #aaa; font-size: 0.82rem; padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
    .progress-panel {
        width: min(1360px, 100%);
        margin-inline: auto;
        max-height: 260px;
        overflow-y: auto;
        padding: 12px 16px;
        border: 1px solid #e8e8e8;
        border-radius: 2px;
        background: #fff;
    }
    .upload-panel {
        width: min(1360px, 100%);
        margin-inline: auto;
        padding: 24px 16px;
        border: 1px solid #e8e8e8;
        border-radius: 2px;
        background: #fff;
    }
</style>
"""


def build_receiver_page(token: str | None = None, host: str | None = None, pin: str | None = None) -> None:
    ui.add_head_html(STYLE)
    cfg = AppConfig.load()

    with ui.column().classes("w-full max-w-[1420px] mx-auto p-8 gap-6"):
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
            receiver_disabled = receiver["status"] == "disabled"
            upload_allowed = bool(receiver.get("upload_allowed"))
        else:
            if not host or not pin:
                ui.label("需要 host 与 PIN").classes("text-negative")
                return
            client = ReceiverClient(host, pin, max_parallel=cfg.max_parallel)
            ui.label("接收端").classes("page-title")
            receiver_disabled = False
            upload_allowed = False

        ui.label(f"Sender · {host}").classes("muted")
        if receiver_disabled:
            ui.label("该接收端已被发送端禁用，无法下载或上传文件。").classes("text-negative")

        if upload_allowed:
            with ui.tabs().classes("w-full") as tabs:
                t_download = ui.tab("文件下载")
                t_upload = ui.tab("上传文件")
            with ui.tab_panels(tabs, value=t_download).classes("w-full"):
                with ui.tab_panel(t_download):
                    _build_download_tab(client, token=token, pin=pin, receiver_disabled=receiver_disabled)
                with ui.tab_panel(t_upload):
                    _build_upload_tab(client, receiver_disabled=receiver_disabled)
        else:
            _build_download_tab(client, token=token, pin=pin, receiver_disabled=receiver_disabled)


def _build_download_tab(
    client: ReceiverClient,
    *,
    token: str | None,
    pin: str | None,
    receiver_disabled: bool,
) -> None:
    with ui.column().classes("w-full gap-3"):
        file_list = ui.column().classes("w-full gap-3")
        selected: dict[str, bool] = {}
        expanded: set[str] = set()
        root_nodes: list[FileTreeNode] = []
        catalog_state: dict[str, str | None] = {"version": None}

        ui.label("文件会保存到当前浏览器的下载目录；如需每次选择位置，请开启浏览器的“下载前询问保存位置”。").classes("muted")
        ui.label("列表会自动同步发送端开放的文件，无需手动刷新。").classes("muted")
        with ui.element("div").classes("file-toolbar"):
            with ui.row().classes("w-full items-center justify-between gap-3"):
                selected_label = ui.label("已选择 0 项").classes("muted")
                with ui.row().classes("gap-2"):
                    ui.button("全选", on_click=lambda _e: select_all()).props("flat dense")
                    ui.button("清空选择", on_click=lambda _e: clear_selection()).props("flat dense")
                    download_btn = ui.button("下载已选").props("unelevated color=primary dense")
                    if receiver_disabled:
                        download_btn.disable()

        def update_selection_summary() -> None:
            count = count_selected(selected)
            selected_label.text = f"已选择 {count} 项"
            if count and not receiver_disabled:
                download_btn.enable()
            else:
                download_btn.disable()

        async def ensure_children(node: FileTreeNode, *, force: bool = False) -> None:
            if not node.is_dir or not node.file_id:
                return
            if force:
                node.children = []
            elif node.children and tree_has_sizes(node):
                return
            tree = await client.get_tree(node.file_id)
            node.children = tree_entries_to_nodes(node.file_id, node.name, tree)
            register_subtree_keys(selected, node)

        def prune_selection() -> None:
            valid_keys = {n.key for root in root_nodes for n in iter_nodes(root)}
            for key in list(selected):
                if key not in valid_keys:
                    selected.pop(key, None)

        async def refresh_expanded_trees(*, force: bool = False) -> None:
            for node in root_nodes:
                if not node.is_dir:
                    continue
                if node.key in expanded:
                    await ensure_children(node, force=force)
                elif force:
                    node.children = []

        async def sync_from_server(*, force_trees: bool = False) -> None:
            files = await client.list_files()
            await sync_root_nodes(files)
            await refresh_expanded_trees(force=force_trees)
            prune_selection()
            catalog_state["version"] = await client.get_catalog_version()
            update_selection_summary()
            render_tree()

        async def sync_root_nodes(files: list[dict[str, Any]]) -> None:
            old_by_id = {n.file_id: n for n in root_nodes if n.file_id}
            merged: list[FileTreeNode] = []
            for item in files:
                file_id = str(item["id"])
                if file_id in old_by_id:
                    node = old_by_id[file_id]
                    node.raw = item
                    node.name = str(item["name"])
                    node.is_dir = bool(item["is_dir"])
                else:
                    node = api_item_to_node(item)
                register_subtree_keys(selected, node)
                if node.is_dir and node.key in expanded:
                    await ensure_children(node)
                merged.append(node)
            root_nodes[:] = merged

            active_root_ids = {n.file_id for n in root_nodes if n.file_id}
            root_keys = {n.key for n in root_nodes}
            for key in list(selected):
                if key.startswith("root:") and key not in root_keys:
                    selected.pop(key, None)
                elif key.startswith("child:"):
                    parts = key.split(":", 2)
                    if len(parts) >= 2 and parts[1] not in active_root_ids:
                        selected.pop(key, None)

        def render_tree() -> None:
            file_list.clear()
            with file_list:
                if not root_nodes:
                    ui.label("暂无可下载文件。").classes("muted")
                    return

                nodes_by_key, parent_by_key = index_nodes(root_nodes)
                with ui.element("div").classes("file-tree"):
                    _render_file_header()
                    for node in root_nodes:
                        _render_tree_node(
                            node,
                            selected=selected,
                            expanded=expanded,
                            nodes_by_key=nodes_by_key,
                            parent_by_key=parent_by_key,
                            ensure_children=ensure_children,
                            render_tree=render_tree,
                            update_selection_summary=update_selection_summary,
                            depth=0,
                        )

        async def select_all() -> None:
            for node in root_nodes:
                if node.is_dir:
                    await ensure_children(node)
                set_subtree_selected(selected, node, True)
            update_selection_summary()
            render_tree()
            ui.notify("已选择全部项目", type="positive")

        def clear_selection() -> None:
            for key in list(selected):
                selected[key] = False
            update_selection_summary()
            render_tree()
            ui.notify("已清空选择", type="info")

        async def load_files() -> None:
            try:
                await sync_from_server(force_trees=True)
            except Exception as ex:
                file_list.clear()
                with file_list:
                    ui.label(f"无法加载文件列表：{ex}").classes("text-negative")

        async def poll_updates() -> None:
            if receiver_disabled:
                return
            try:
                version = await client.get_catalog_version()
            except Exception:
                return
            if catalog_state["version"] is None:
                catalog_state["version"] = version
                return
            if version == catalog_state["version"]:
                return
            try:
                await sync_from_server(force_trees=True)
            except Exception:
                return

        async def do_download() -> None:
            if receiver_disabled:
                ui.notify("该接收端已被禁用", type="negative")
                return
            if not count_selected(selected):
                ui.notify("请选择文件", type="warning")
                return
            urls = resolve_browser_download_urls(
                selected,
                root_nodes,
                token=token,
                pin=pin,
            )
            if not urls:
                ui.notify("没有可下载的文件", type="warning")
                return

            progress_area.clear()
            with progress_area:
                ui.label("已交给浏览器下载").classes("muted")
                ui.label("下载进度由浏览器管理，不会写入发送端电脑。文件夹会下载为 ZIP。").classes("muted")
            ui.run_javascript(_download_script(urls))
            ui.notify("已开始浏览器下载", type="positive")

        async def start_download(_e: Any = None) -> None:
            await do_download()

        download_btn.on("click", start_download)
        update_selection_summary()

        with ui.row().classes("gap-2"):
            ui.button("立即刷新", on_click=load_files).props("flat")
        progress_area = ui.column().classes("progress-panel")
        with progress_area:
            ui.label("等待下载任务...").classes("muted")
        ui.timer(0.1, load_files, once=True)
        ui.timer(2.0, poll_updates)


def _build_upload_tab(client: ReceiverClient, *, receiver_disabled: bool) -> None:
    with ui.column().classes("w-full gap-3"):
        ui.label("选择文件上传到发送端电脑的存放目录。").classes("muted")

        upload_log = ui.column().classes("w-full gap-1")

        async def handle_upload(e: UploadEventArguments) -> None:
            if receiver_disabled:
                ui.notify("该接收端已被禁用", type="negative")
                return
            filename = e.file.name
            try:
                data = await e.file.read()
                record = await client.upload_file(filename, data)
                with upload_log:
                    ui.label(
                        f"已上传 · {record['name']} · {record.get('size_human', record['size'])}"
                    ).classes("text-sm")
                ui.notify(f"已上传 {record['name']}", type="positive")
            except Exception as ex:
                ui.notify(f"上传失败：{ex}", type="negative")

        with ui.element("div").classes("upload-panel"):
            upload_widget = ui.upload(
                on_upload=handle_upload,
                auto_upload=True,
                multiple=True,
                label="选择文件上传",
            ).classes("w-full")
            if receiver_disabled:
                upload_widget.disable()


def _render_file_header() -> None:
    with ui.element("div").classes("file-row file-row-head"):
        ui.label("").classes("select-cell")
        ui.label("名称").classes("file-cell")
        ui.label("类型").classes("file-cell")
        ui.label("大小").classes("file-cell")
        ui.label("位置").classes("file-cell")
        ui.label("时间").classes("file-cell")
        ui.label("操作").classes("file-cell")


def _render_tree_node(
    node: FileTreeNode,
    *,
    selected: dict[str, bool],
    expanded: set[str],
    nodes_by_key: dict[str, FileTreeNode],
    parent_by_key: dict[str, str],
    ensure_children: Any,
    render_tree: Any,
    update_selection_summary: Any,
    depth: int,
) -> None:
    is_dir = node.is_dir
    is_expanded = node.key in expanded

    async def toggle_expand() -> None:
        if node.key in expanded:
            expanded.remove(node.key)
        else:
            expanded.add(node.key)
            await ensure_children(node)
        render_tree()

    async def toggle_selection(e: ValueChangeEventArguments[bool | None]) -> None:
        checked = bool(e.value)
        if checked and is_dir:
            await ensure_children(node)
        set_subtree_selected(selected, node, checked)
        if not checked:
            uncheck_ancestors(node, parent_by_key, nodes_by_key, selected)
        update_selection_summary()
        render_tree()

    item = node.raw or {}
    with ui.element("div").classes("file-row"):
        with ui.element("div").classes("select-cell"):
            ui.checkbox(
                value=bool(selected.get(node.key, False)),
                on_change=toggle_selection,
            ).props("dense")
        with ui.element("div").classes("file-cell file-name-cell").style(f"padding-left: {depth * 22}px"):
            if is_dir:
                ui.button("−" if is_expanded else "+", on_click=toggle_expand).props("flat dense round").classes("text-grey-7")
            else:
                ui.element("span").classes("expand-spacer")
            ui.icon("folder" if is_dir else "insert_drive_file").classes("text-grey-7")
            ui.label(node.name).classes("file-name-text")
        ui.label("文件夹" if is_dir else "文件").classes("file-cell muted")
        ui.label(_size_text(item)).classes("file-cell muted")
        ui.label(_location_text(node)).classes("file-cell muted")
        ui.label(_time_text(item)).classes("file-cell muted")
        ui.button("详情", on_click=lambda _e, n=node: _show_details(n)).props("flat dense")

    if is_dir and is_expanded:
        if not node.children:
            ui.label("空文件夹").classes("tree-note").style(f"padding-left: {depth * 22 + 46}px")
            return
        for child in node.children:
            _render_tree_node(
                child,
                selected=selected,
                expanded=expanded,
                nodes_by_key=nodes_by_key,
                parent_by_key=parent_by_key,
                ensure_children=ensure_children,
                render_tree=render_tree,
                update_selection_summary=update_selection_summary,
                depth=depth + 1,
            )


def _size_text(item: dict[str, Any]) -> str:
    if "size_human" in item:
        return str(item["size_human"])
    return format_size(int(item.get("size", 0)))


def _location_text(node: FileTreeNode) -> str:
    if node.relative_path:
        return node.relative_path
    raw = node.raw or {}
    return str(raw.get("path") or node.name)


def _time_text(item: dict[str, Any]) -> str:
    return str(item.get("uploaded_at") or item.get("status") or "-")


def _show_details(node: FileTreeNode) -> None:
    item = node.raw or {"name": node.name, "is_dir": node.is_dir}
    details = [
        ("名称", node.name),
        ("类型", "文件夹" if node.is_dir else "文件"),
        ("大小", _size_text(item)),
        ("位置", _location_text(node)),
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


def _download_script(urls: list[str]) -> str:
    return f"""
(async () => {{
    const urls = {json.dumps(urls)};
    for (const url of urls) {{
        const link = document.createElement('a');
        link.href = url;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        link.remove();
        await new Promise(resolve => setTimeout(resolve, 250));
    }}
}})();
"""
