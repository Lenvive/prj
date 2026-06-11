"""Sender GUI — minimalist tabs for file transfer, receivers, settings."""

from __future__ import annotations

from datetime import datetime
import json
import webbrowser
from pathlib import Path
from typing import Any

import uvicorn
from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from pylocalsend.core.file_handler.file_handler import format_size
from pylocalsend.core.transfer.server_entry import prepare_service
from pylocalsend.core.utils.config import APP_DIR, AppConfig
from pylocalsend.core.utils.network import connect_host
from pylocalsend.gui.facade import SenderFacade
from pylocalsend.gui.sender.auth import (
    ensure_gui_auth_config,
    guard_sender_page,
    gui_storage_secret,
    print_startup_access_info,
    sender_url_with_pin,
)
from pylocalsend.gui.file_tree import (
    FileTreeNode,
    apply_grants_to_selected,
    compute_grants,
    count_selected,
    index_nodes,
    local_children_to_nodes,
    local_item_to_node,
    register_subtree_keys,
    set_subtree_selected,
    uncheck_ancestors,
)

# 原研哉风格：留白、低对比、克制用色
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
        grid-template-columns: 40px minmax(240px, 1.2fr) 90px 110px minmax(280px, 1fr) 160px minmax(220px, auto);
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
    .receiver-row {
        display: grid;
        grid-template-columns: 160px minmax(300px, 1fr) 100px 90px 100px minmax(380px, auto);
        gap: 16px;
        align-items: center;
        box-sizing: border-box;
        width: 100%;
        min-width: 1040px;
        min-height: 44px;
        padding: 8px 16px;
        border-bottom: 1px solid #f0f0f0;
    }
    .receiver-row:last-child { border-bottom: none; }
</style>
"""


def run_sender_gui() -> None:
    cfg = AppConfig.load()
    ensure_gui_auth_config(cfg)
    service = prepare_service(cfg)
    facade = SenderFacade()
    app = service.app

    @ui.page("/")
    def sender_home() -> None:
        def build_home() -> None:
            ui.add_head_html(STYLE)
            with ui.column().classes("w-full max-w-[1420px] mx-auto p-8 gap-6"):
                ui.label("PyLocalSend").classes("page-title")
                with ui.column().classes("gap-0"):
                    for label, url in facade.access_urls.labels():
                        ui.label(f"{label} · {url}").classes("muted")
                    if facade.access_urls.public:
                        ui.label("公网地址需路由器端口映射后才可从外网访问").classes("muted text-xs")

                with ui.tabs().classes("w-full") as tabs:
                    t_files = ui.tab("文件传输")
                    t_recv = ui.tab("接收端管理")
                    t_settings = ui.tab("设置")

                with ui.tab_panels(tabs, value=t_files).classes("w-full"):
                    with ui.tab_panel(t_files):
                        _files_tab(facade)
                    with ui.tab_panel(t_recv):
                        _receivers_tab(facade)
                    with ui.tab_panel(t_settings):
                        _settings_tab(facade)

        guard_sender_page(facade.service.config, STYLE, build_home)

    @ui.page("/r/{token}")
    def receiver_by_token(token: str) -> None:
        from pylocalsend.gui.receiver.webui import build_receiver_page

        build_receiver_page(token=token)

    print_startup_access_info(cfg, service.access_urls)

    ui.run_with(
        app,
        title="PyLocalSend",
        storage_secret=gui_storage_secret(cfg),
        show_welcome_message=False,
    )

    host = cfg.host if cfg.host != "0.0.0.0" else "0.0.0.0"
    local_base = f"http://{connect_host(cfg.host)}:{cfg.port}"
    webbrowser.open(sender_url_with_pin(local_base, cfg.server_pin))
    uvicorn.run(app, host=host, port=cfg.port, log_level="warning")


def _files_tab(facade: SenderFacade) -> None:
    with ui.row().classes("w-full items-end gap-3"):
        path_input = ui.input("绝对路径（文件或文件夹）").classes("grow").props("outlined dense")
        upload_btn = ui.button("确认上传").props("unelevated color=primary")
    expanded: set[str] = set()
    selected: dict[str, bool] = {}
    root_nodes: list[FileTreeNode] = []
    files_container = ui.column().classes("w-full gap-3")

    with ui.element("div").classes("file-toolbar"):
        with ui.row().classes("w-full items-center justify-between gap-3"):
            selected_label = ui.label("已开放 0 项可下载").classes("muted")
            with ui.row().classes("gap-2"):
                ui.button("全部开放", on_click=lambda _e: enable_all()).props("flat dense")
                ui.button("全部关闭", on_click=lambda _e: disable_all()).props("flat dense")

    ui.label("勾选表示对接收端开放下载；未勾选项接收端不可见也不可下载。").classes("muted")

    def update_selection_summary() -> None:
        selected_label.text = f"已开放 {count_selected(selected)} 项可下载"

    def persist_grants(root_node: FileTreeNode) -> None:
        if not root_node.file_id:
            return
        facade.set_download_grants(root_node.file_id, compute_grants(root_node, selected))

    def ensure_local_children(node: FileTreeNode, root_base: str | None) -> None:
        if not node.is_dir or not node.raw:
            return
        if not node.children:
            children = facade.folder_path_contents(str(node.raw["path"]))
            node.children = local_children_to_nodes(node, children, root_base=root_base)
            register_subtree_keys(selected, node)
        for child in node.children:
            if child.is_dir:
                ensure_local_children(child, root_base)

    def enable_all() -> None:
        for node in root_nodes:
            base = str(node.raw["path"]) if node.raw and node.is_dir else None
            if node.is_dir:
                ensure_local_children(node, base)
            set_subtree_selected(selected, node, True)
            if node.file_id:
                facade.set_download_grants(node.file_id, {""})
        update_selection_summary()
        refresh()
        ui.notify("已全部开放下载", type="positive")

    def disable_all() -> None:
        for key in list(selected):
            selected[key] = False
        for node in root_nodes:
            if node.file_id:
                facade.set_download_grants(node.file_id, set())
        update_selection_summary()
        refresh()
        ui.notify("已全部关闭下载", type="info")

    def refresh() -> None:
        files_container.clear()
        with files_container:
            files = facade.list_files()
            if not files:
                ui.label("暂无已注册文件。").classes("muted")
                return

            old_by_id = {n.file_id: n for n in root_nodes if n.file_id}
            root_nodes.clear()
            for item in files:
                file_id = str(item["id"])
                if file_id in old_by_id:
                    node = old_by_id[file_id]
                    node.raw = item
                    node.name = str(item["name"])
                    node.is_dir = bool(item["is_dir"])
                else:
                    node = local_item_to_node(item, registered=True)
                register_subtree_keys(selected, node)
                apply_grants_to_selected(node, facade.get_download_grants(file_id), selected)
                if node.key in expanded:
                    ensure_local_children(
                        node,
                        str(item["path"]) if item["is_dir"] else None,
                    )
                root_nodes.append(node)

            root_keys = {node.key for node in root_nodes}
            for key in list(selected):
                if key.startswith("root:") and key not in root_keys:
                    selected.pop(key, None)
            update_selection_summary()

            nodes_by_key, parent_by_key = index_nodes(root_nodes)

            with ui.element("div").classes("file-tree"):
                _render_file_header()
                for node in root_nodes:
                    _render_file_node(
                        facade,
                        node,
                        depth=0,
                        expanded=expanded,
                        selected=selected,
                        nodes_by_key=nodes_by_key,
                        parent_by_key=parent_by_key,
                        root_base=str(node.raw["path"]) if node.raw and node.is_dir else None,
                        ensure_local_children=ensure_local_children,
                        refresh=refresh,
                        update_selection_summary=update_selection_summary,
                        persist_grants=persist_grants,
                        file_root=node,
                        registered=True,
                    )

    def do_upload() -> None:
        raw = path_input.value.strip()
        if not raw:
            ui.notify("请输入路径", type="warning")
            return
        try:
            facade.register_paths([raw])
            path_input.value = ""
            refresh()
            ui.notify("已注册", type="positive")
        except Exception as ex:
            ui.notify(str(ex), type="negative")

    upload_btn.on_click(do_upload)
    refresh()


def _render_file_header() -> None:
    with ui.element("div").classes("file-row file-row-head"):
        ui.label("开放").classes("select-cell")
        ui.label("名称").classes("file-cell")
        ui.label("类型").classes("file-cell")
        ui.label("大小").classes("file-cell")
        ui.label("位置").classes("file-cell")
        ui.label("时间").classes("file-cell")
        ui.label("操作").classes("file-cell")


def _render_file_node(
    facade: SenderFacade,
    node: FileTreeNode,
    *,
    depth: int,
    expanded: set[str],
    selected: dict[str, bool],
    nodes_by_key: dict[str, FileTreeNode],
    parent_by_key: dict[str, str],
    root_base: str | None,
    ensure_local_children: Any,
    refresh: Any,
    update_selection_summary: Any,
    persist_grants: Any,
    file_root: FileTreeNode,
    registered: bool,
) -> None:
    item = node.raw or {"name": node.name, "is_dir": node.is_dir, "path": node.relative_path}
    is_dir = node.is_dir
    is_expanded = node.key in expanded

    def toggle_expand() -> None:
        if node.key in expanded:
            expanded.remove(node.key)
        else:
            expanded.add(node.key)
            ensure_local_children(node, root_base)
        refresh()

    def toggle_selection(e: ValueChangeEventArguments[bool | None]) -> None:
        checked = bool(e.value)
        if checked and is_dir:
            ensure_local_children(node, root_base)
        set_subtree_selected(selected, node, checked)
        if not checked:
            uncheck_ancestors(node, parent_by_key, nodes_by_key, selected)
        persist_grants(file_root)
        update_selection_summary()
        refresh()

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
        ui.label(_file_size_text(item)).classes("file-cell muted")
        ui.label(str(item.get("path", node.relative_path))).classes("file-cell muted")
        ui.label(_file_time_text(item, registered)).classes("file-cell muted")
        with ui.row().classes("gap-1"):
            ui.button(
                "详情",
                on_click=lambda _e, n=dict(item), is_registered=registered: _show_file_details(
                    n,
                    is_registered,
                ),
            ).props("flat dense")
            if registered and node.file_id:
                ui.button(
                    "下载记录",
                    on_click=lambda _e, fid=node.file_id: _show_downloads(facade, fid),
                ).props("flat dense")
                ui.button(
                    "删除",
                    on_click=lambda _e, fid=node.file_id: _remove_file(facade, fid, refresh),
                ).props("flat dense color=negative")

    if is_dir and is_expanded:
        if not node.children:
            try:
                ensure_local_children(node, root_base)
            except Exception as ex:
                ui.label(f"无法读取目录：{ex}").classes("tree-note").style(f"padding-left: {depth * 22 + 46}px")
                return

        if not node.children:
            ui.label("空文件夹").classes("tree-note").style(f"padding-left: {depth * 22 + 46}px")
            return

        for child in node.children:
            _render_file_node(
                facade,
                child,
                depth=depth + 1,
                expanded=expanded,
                selected=selected,
                nodes_by_key=nodes_by_key,
                parent_by_key=parent_by_key,
                root_base=root_base,
                ensure_local_children=ensure_local_children,
                refresh=refresh,
                update_selection_summary=update_selection_summary,
                persist_grants=persist_grants,
                file_root=file_root,
                registered=False,
            )


def _file_size_text(item: dict[str, Any]) -> str:
    if "size_human" in item:
        return str(item["size_human"])
    return format_size(int(item["size"]))


def _file_time_text(item: dict[str, Any], registered: bool) -> str:
    if registered:
        return f"{item['status']} · {item['uploaded_at']}"
    return datetime.fromtimestamp(float(item["mtime"])).strftime("%Y-%m-%d %H:%M:%S")


def _remove_file(facade: SenderFacade, file_id: str, refresh: Any) -> None:
    facade.remove_file(file_id)
    refresh()


def _show_file_details(item: dict[str, Any], registered: bool) -> None:
    details = [
        ("名称", item["name"]),
        ("类型", "文件夹" if item["is_dir"] else "文件"),
        ("大小", _file_size_text(item)),
        ("路径", item["path"]),
        ("时间", _file_time_text(item, registered)),
    ]
    if registered:
        details.extend(
            [
                ("ID", item["id"]),
                ("状态", item["status"]),
            ]
        )

    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96 max-w-3xl"):
        ui.label("文件详情").classes("page-title mb-4")
        for label, value in details:
            with ui.row().classes("w-full items-start gap-3"):
                ui.label(f"{label}:").classes("muted").style("width: 64px; min-width: 64px;")
                ui.label(str(value)).classes("text-sm break-all")
        ui.button("关闭", on_click=dlg.close).props("flat")
    dlg.open()


async def _show_downloads(facade: SenderFacade, file_id: str) -> None:
    logs = facade.file_downloads(file_id)
    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96"):
        ui.label("下载记录").classes("page-title mb-4")
        if not logs:
            ui.label("暂无").classes("muted")
        for log in logs:
            ui.label(
                f"{log['downloader']} · {log['started_at']} · {log['status']}"
            ).classes("text-sm")
        ui.button("关闭", on_click=dlg.close)
    dlg.open()


def _receivers_tab(facade: SenderFacade) -> None:
    name_input = ui.input("接收端名称").props("outlined dense")
    pin_input = ui.input("PIN（留空自动生成）").props("outlined dense")
    container = ui.column().classes("w-full gap-3")

    def refresh() -> None:
        container.clear()
        with container:
            receivers = facade.list_receivers()
            if not receivers:
                ui.label("暂无接收端。").classes("muted")
                return

            with ui.element("div").classes("file-tree"):
                _render_receiver_header()
                for r in receivers:
                    _render_receiver_row(facade, r, refresh)

    def create() -> None:
        name = name_input.value.strip()
        if not name:
            ui.notify("请输入名称", type="warning")
            return
        pin = pin_input.value.strip() or None
        rec = facade.create_receiver(name, pin)
        ui.notify(f"已创建: {rec['link']}", type="positive")
        name_input.value = ""
        pin_input.value = ""
        refresh()

    ui.button("创建接收端", on_click=create).props("unelevated")
    refresh()


def _render_receiver_header() -> None:
    with ui.element("div").classes("receiver-row file-row-head"):
        ui.label("名称").classes("file-cell")
        ui.label("链接").classes("file-cell")
        ui.label("状态").classes("file-cell")
        ui.label("上传").classes("file-cell")
        ui.label("PIN").classes("file-cell")
        ui.label("操作").classes("file-cell")


def _receiver_status_label(status: str) -> str:
    return {"active": "正常", "disabled": "已禁用"}.get(status, status)


def _receiver_upload_label(upload_allowed: bool) -> str:
    return "已允许" if upload_allowed else "未允许"


def _render_receiver_row(
    facade: SenderFacade,
    receiver: dict[str, Any],
    refresh: Any,
) -> None:
    with ui.element("div").classes("receiver-row"):
        ui.label(str(receiver["name"])).classes("file-cell")
        ui.label(str(receiver["link"])).classes("file-cell muted")
        ui.label(_receiver_status_label(str(receiver["status"]))).classes("file-cell muted")
        ui.label(_receiver_upload_label(bool(receiver.get("upload_allowed")))).classes("file-cell muted")
        ui.label(str(receiver["pin"])).classes("file-cell muted")
        with ui.row().classes("gap-1"):
            ui.button(
                "下载记录",
                on_click=lambda _e, rid=receiver["id"]: _show_receiver_downloads(facade, rid),
            ).props("flat dense")
            ui.button(
                "复制链接",
                on_click=lambda _e, node=dict(receiver): _show_receiver_links(facade, node),
            ).props("flat dense")
            if receiver["status"] == "active":
                ui.button(
                    "禁用",
                    on_click=lambda _e, rid=receiver["id"]: _disable_receiver(facade, rid, refresh),
                ).props("flat dense color=warning")
            elif receiver["status"] == "disabled":
                ui.button(
                    "启用",
                    on_click=lambda _e, rid=receiver["id"]: _enable_receiver(facade, rid, refresh),
                ).props("flat dense color=positive")
            if receiver.get("upload_allowed"):
                ui.button(
                    "禁止上传",
                    on_click=lambda _e, rid=receiver["id"]: _disallow_receiver_upload(
                        facade, rid, refresh
                    ),
                ).props("flat dense")
            else:
                ui.button(
                    "允许上传",
                    on_click=lambda _e, rid=receiver["id"]: _allow_receiver_upload(
                        facade, rid, refresh
                    ),
                ).props("flat dense color=primary")
            ui.button(
                "删除",
                on_click=lambda _e, rid=receiver["id"]: _remove_receiver(facade, rid, refresh),
            ).props("flat dense color=negative")


def _disable_receiver(facade: SenderFacade, receiver_id: str, refresh: Any) -> None:
    facade.disable_receiver(receiver_id)
    ui.notify("已禁用该接收端，进行中的下载已停止", type="info")
    refresh()


def _enable_receiver(facade: SenderFacade, receiver_id: str, refresh: Any) -> None:
    facade.enable_receiver(receiver_id)
    ui.notify("已解除禁用，该接收端可继续下载", type="positive")
    refresh()


def _allow_receiver_upload(facade: SenderFacade, receiver_id: str, refresh: Any) -> None:
    facade.allow_receiver_upload(receiver_id)
    ui.notify("已允许该接收端通过浏览器上传文件", type="positive")
    refresh()


def _disallow_receiver_upload(facade: SenderFacade, receiver_id: str, refresh: Any) -> None:
    facade.disallow_receiver_upload(receiver_id)
    ui.notify("已禁止该接收端通过浏览器上传文件", type="info")
    refresh()


def _remove_receiver(facade: SenderFacade, receiver_id: str, refresh: Any) -> None:
    facade.remove_receiver(receiver_id)
    refresh()


async def _show_receiver_downloads(facade: SenderFacade, receiver_id: str) -> None:
    logs = facade.receiver_downloads(receiver_id)
    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96"):
        ui.label("接收端下载记录").classes("page-title mb-4")
        if not logs:
            ui.label("暂无").classes("muted")
        for log in logs:
            ui.label(
                f"{log.get('file_name', '?')} · {log['downloader']} · {log['status']}"
            ).classes("text-sm")
        ui.button("关闭", on_click=dlg.close)
    dlg.open()


def _show_receiver_links(facade: SenderFacade, receiver: dict[str, Any]) -> None:
    token = str(receiver["token"])
    links = [
        (label, f"{url.rstrip('/')}/r/{token}")
        for label, url in facade.access_urls.labels()
    ]

    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96 max-w-3xl"):
        ui.label(f"复制链接 · {receiver['name']}").classes("page-title mb-4")
        for label, link in links:
            with ui.row().classes("w-full items-center gap-3 no-wrap"):
                ui.label(label).classes("muted").style("width: 72px; min-width: 72px;")
                ui.label(link).classes("text-sm break-all grow")
                ui.button(
                    "复制",
                    on_click=lambda _e, text=link: _copy_to_clipboard(text),
                ).props("flat dense")
        ui.button("关闭", on_click=dlg.close).props("flat")
    dlg.open()


def _copy_to_clipboard(text: str) -> None:
    ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(text)})")
    ui.notify("已复制到粘贴板", type="positive")


def _settings_tab(facade: SenderFacade) -> None:
    cfg = facade.get_config()
    default_upload_dir = APP_DIR / "browser_uploads"
    with ui.column().classes("w-full max-w-2xl gap-4"):
        chunk_input = ui.input("分片大小（字节）", value=str(cfg["chunk_size"])).props(
            "outlined dense"
        )
        upload_input = ui.input(
            "浏览器上传存放路径",
            value=str(cfg.get("upload_dir") or ""),
            placeholder=str(default_upload_dir),
        ).props("outlined dense").classes("w-full")
        ui.label(
            f"接收端通过浏览器上传的文件会保存到此目录（按接收端名称分子文件夹）。"
            f"留空则使用默认路径：{default_upload_dir}"
        ).classes("muted")

        def save() -> None:
            try:
                updates: dict[str, Any] = {"chunk_size": int(chunk_input.value)}
                raw_upload = upload_input.value.strip()
                if raw_upload:
                    upload_path = Path(raw_upload).expanduser()
                    upload_path.mkdir(parents=True, exist_ok=True)
                updates["upload_dir"] = raw_upload
                facade.update_config(updates)
                ui.notify("已保存", type="positive")
            except Exception as ex:
                ui.notify(f"保存失败：{ex}", type="negative")

        ui.button("保存设置", on_click=save).props("unelevated")
