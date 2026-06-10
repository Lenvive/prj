"""Sender GUI — minimalist tabs for file transfer, receivers, settings."""

from __future__ import annotations

from datetime import datetime
import json
import webbrowser
from typing import Any

import uvicorn
from nicegui import ui

from pylocalsend.core.file_handler.file_handler import format_size
from pylocalsend.core.transfer.server_entry import prepare_service
from pylocalsend.core.utils.config import AppConfig
from pylocalsend.core.utils.crypto import generate_pin
from pylocalsend.core.utils.network import connect_host
from pylocalsend.gui.facade import SenderFacade

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
    .file-row {
        display: grid;
        grid-template-columns: 260px 90px 110px minmax(300px, 1fr) 160px minmax(300px, auto);
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
    .file-name-cell { display: flex; align-items: center; gap: 6px; min-width: 0; }
    .file-name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .expand-spacer { width: 28px; min-width: 28px; }
    .tree-note { color: #aaa; font-size: 0.82rem; padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
    .receiver-row {
        display: grid;
        grid-template-columns: 160px minmax(360px, 1fr) 100px 100px minmax(320px, auto);
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
    if not cfg.server_pin and cfg.pin_verification_enabled:
        cfg.server_pin = generate_pin()
        cfg.save()
    service = prepare_service(cfg)
    facade = SenderFacade()
    app = service.app

    @ui.page("/")
    def sender_home() -> None:
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

    @ui.page("/r/{token}")
    def receiver_by_token(token: str) -> None:
        from pylocalsend.gui.receiver.webui import build_receiver_page

        build_receiver_page(token=token)

    ui.run_with(app, title="PyLocalSend")

    host = cfg.host if cfg.host != "0.0.0.0" else "0.0.0.0"
    webbrowser.open(f"http://{connect_host(cfg.host)}:{cfg.port}/")
    uvicorn.run(app, host=host, port=cfg.port, log_level="warning")


def _files_tab(facade: SenderFacade) -> None:
    path_input = ui.input("绝对路径（文件或文件夹）").classes("w-full").props("outlined dense")
    expanded_paths: set[str] = set()
    files_container = ui.column().classes("w-full gap-3")

    def refresh() -> None:
        files_container.clear()
        with files_container:
            files = facade.list_files()
            if not files:
                ui.label("暂无已注册文件。").classes("muted")
                return

            with ui.element("div").classes("file-tree"):
                _render_file_header()
                for f in files:
                    _render_file_node(
                        facade,
                        f,
                        depth=0,
                        expanded_paths=expanded_paths,
                        refresh=refresh,
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

    ui.button("确认上传", on_click=do_upload).props("unelevated color=primary")
    refresh()


def _render_file_header() -> None:
    with ui.element("div").classes("file-row file-row-head"):
        ui.label("名称").classes("file-cell")
        ui.label("类型").classes("file-cell")
        ui.label("大小").classes("file-cell")
        ui.label("位置").classes("file-cell")
        ui.label("时间").classes("file-cell")
        ui.label("操作").classes("file-cell")


def _render_file_node(
    facade: SenderFacade,
    item: dict[str, Any],
    *,
    depth: int,
    expanded_paths: set[str],
    refresh: Any,
    registered: bool,
) -> None:
    is_dir = bool(item["is_dir"])
    path = str(item["path"])
    expanded = path in expanded_paths

    def toggle() -> None:
        if path in expanded_paths:
            expanded_paths.remove(path)
        else:
            expanded_paths.add(path)
        refresh()

    with ui.element("div").classes("file-row"):
        with ui.element("div").classes("file-cell file-name-cell").style(f"padding-left: {depth * 22}px"):
            if is_dir:
                ui.button("−" if expanded else "+", on_click=toggle).props("flat dense round").classes("text-grey-7")
            else:
                ui.element("span").classes("expand-spacer")
            ui.icon("folder" if is_dir else "insert_drive_file").classes("text-grey-7")
            ui.label(str(item["name"])).classes("file-name-text")
        ui.label("文件夹" if is_dir else "文件").classes("file-cell muted")
        ui.label(_file_size_text(item)).classes("file-cell muted")
        ui.label(str(item["path"])).classes("file-cell muted")
        ui.label(_file_time_text(item, registered)).classes("file-cell muted")
        with ui.row().classes("gap-1"):
            ui.button(
                "详情",
                on_click=lambda _e, node=dict(item), is_registered=registered: _show_file_details(
                    node,
                    is_registered,
                ),
            ).props("flat dense")
            if registered:
                ui.button("下载记录", on_click=lambda _e, fid=item["id"]: _show_downloads(facade, fid)).props("flat dense")
                ui.button("删除", on_click=lambda _e, fid=item["id"]: _remove_file(facade, fid, refresh)).props("flat dense color=negative")

    if is_dir and expanded:
        try:
            children = facade.folder_path_contents(path)
        except Exception as ex:
            ui.label(f"无法读取目录：{ex}").classes("tree-note").style(f"padding-left: {depth * 22 + 46}px")
            return

        if not children:
            ui.label("空文件夹").classes("tree-note").style(f"padding-left: {depth * 22 + 46}px")
            return

        for child in children:
            _render_file_node(
                facade,
                child,
                depth=depth + 1,
                expanded_paths=expanded_paths,
                refresh=refresh,
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
        ui.label("PIN").classes("file-cell")
        ui.label("操作").classes("file-cell")


def _receiver_status_label(status: str) -> str:
    return {"active": "正常", "disabled": "已禁用"}.get(status, status)


def _render_receiver_row(
    facade: SenderFacade,
    receiver: dict[str, Any],
    refresh: Any,
) -> None:
    with ui.element("div").classes("receiver-row"):
        ui.label(str(receiver["name"])).classes("file-cell")
        ui.label(str(receiver["link"])).classes("file-cell muted")
        ui.label(_receiver_status_label(str(receiver["status"]))).classes("file-cell muted")
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
    fields = {}

    for key in ("chunk_size", "max_parallel", "encryption_enabled", "pin_verification_enabled", "server_pin"):
        val = cfg[key]
        if isinstance(val, bool):
            fields[key] = ui.switch(key.replace("_", " "), value=val)
        else:
            fields[key] = ui.input(key.replace("_", " "), value=str(val)).props("outlined dense")

    def save() -> None:
        updates = {}
        for key, widget in fields.items():
            v = widget.value
            if isinstance(cfg[key], bool):
                updates[key] = bool(v)
            elif isinstance(cfg[key], int):
                updates[key] = int(v)
            else:
                updates[key] = str(v)
        facade.update_config(updates)
        ui.notify("已保存", type="positive")

    ui.button("保存设置", on_click=save).props("unelevated")
