"""Sender GUI — minimalist tabs for file transfer, receivers, settings."""

from __future__ import annotations

import webbrowser

import uvicorn
from nicegui import ui

from pylocalsend.core.transfer.server_entry import prepare_service
from pylocalsend.core.utils.config import AppConfig
from pylocalsend.core.utils.crypto import generate_pin
from pylocalsend.gui.facade import SenderFacade

# 原研哉风格：留白、低对比、克制用色
STYLE = """
<style>
    body { background: #fafafa; color: #333; font-family: "Segoe UI", "Helvetica Neue", sans-serif; }
    .q-card { box-shadow: none !important; border: 1px solid #e8e8e8; border-radius: 2px; }
    .page-title { font-weight: 300; letter-spacing: 0.08em; font-size: 1.4rem; color: #222; }
    .muted { color: #888; font-size: 0.85rem; }
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
        with ui.column().classes("w-full max-w-5xl mx-auto p-8 gap-6"):
            ui.label("PyLocalSend").classes("page-title")
            ui.label(f"Sender · {facade.base_url}").classes("muted")

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
    browser_host = "127.0.0.1" if cfg.host in ("0.0.0.0", "") else cfg.host
    webbrowser.open(f"http://{browser_host}:{cfg.port}/")
    uvicorn.run(app, host=host, port=cfg.port, log_level="warning")


def _files_tab(facade: SenderFacade) -> None:
    path_input = ui.input("绝对路径（文件或文件夹）").classes("w-full").props("outlined dense")
    files_container = ui.column().classes("w-full gap-2")

    def refresh() -> None:
        files_container.clear()
        with files_container:
            for f in facade.list_files():
                with ui.card().classes("w-full p-4"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(f["name"]).classes("text-base")
                        ui.label(f"{f['size_human']} · {f['status']}").classes("muted")
                    ui.label(f["path"]).classes("muted text-xs")
                    ui.label(f"上传于 {f['uploaded_at']}").classes("muted text-xs")

                    async def show_contents(_e, fid=f["id"], name=f["name"]) -> None:
                        if not f["is_dir"]:
                            return
                        items = facade.folder_contents(fid)
                        with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96"):
                            ui.label(name).classes("page-title mb-4")
                            for item in items:
                                kind = "📁" if item["is_dir"] else "📄"
                                ui.label(f"{kind} {item['name']}  ({item['size']} B)")
                            ui.button("关闭", on_click=dlg.close)
                        dlg.open()

                    async def show_downloads(_e, fid=f["id"]) -> None:
                        logs = facade.file_downloads(fid)
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

                    def remove(fid=f["id"]) -> None:
                        facade.remove_file(fid)
                        refresh()

                    with ui.row().classes("gap-2 mt-2"):
                        if f["is_dir"]:
                            ui.button("查看内容", on_click=show_contents).props("flat dense")
                        ui.button("下载记录", on_click=show_downloads).props("flat dense")
                        ui.button("删除", on_click=remove).props("flat dense color=negative")

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


def _receivers_tab(facade: SenderFacade) -> None:
    name_input = ui.input("接收端名称").props("outlined dense")
    pin_input = ui.input("PIN（留空自动生成）").props("outlined dense")
    container = ui.column().classes("w-full gap-2")

    def refresh() -> None:
        container.clear()
        with container:
            for r in facade.list_receivers():
                with ui.card().classes("w-full p-4"):
                    ui.label(r["name"]).classes("text-base")
                    ui.label(r["link"]).classes("muted text-sm break-all")
                    ui.label(f"状态: {r['status']} · PIN: {r['pin']}").classes("muted text-xs")

                    async def show_dl(_e, rid=r["id"]) -> None:
                        logs = facade.receiver_downloads(rid)
                        with ui.dialog() as dlg, ui.card().classes("p-6"):
                            ui.label("接收端下载记录").classes("page-title mb-4")
                            for log in logs:
                                ui.label(
                                    f"{log.get('file_name','?')} · {log['downloader']} · {log['status']}"
                                ).classes("text-sm")
                            ui.button("关闭", on_click=dlg.close)
                        dlg.open()

                    def remove(rid=r["id"]) -> None:
                        facade.remove_receiver(rid)
                        refresh()

                    with ui.row().classes("gap-2 mt-2"):
                        ui.button("下载记录", on_click=show_dl).props("flat dense")
                        ui.button("删除", on_click=remove).props("flat dense color=negative")

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
