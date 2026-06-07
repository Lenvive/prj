"""Receiver WebUI — browse and download with progress."""

from __future__ import annotations

import asyncio
from pathlib import Path

from nicegui import ui

from pylocalsend.core.receiver.receiver import ReceiverClient
from pylocalsend.core.transfer.server_entry import get_service
from pylocalsend.core.utils.config import AppConfig

STYLE = """
<style>
    body { background: #fafafa; color: #333; font-family: "Segoe UI", "Helvetica Neue", sans-serif; }
    .q-card { box-shadow: none !important; border: 1px solid #e8e8e8; border-radius: 2px; }
    .page-title { font-weight: 300; letter-spacing: 0.08em; font-size: 1.4rem; }
    .muted { color: #888; font-size: 0.85rem; }
</style>
"""


def build_receiver_page(token: str | None = None, host: str | None = None, pin: str | None = None) -> None:
    ui.add_head_html(STYLE)
    cfg = AppConfig.load()

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

    dest_input = ui.input("下载目录（绝对路径）", value=str(Path.home() / "Downloads")).classes("w-full").props("outlined")
    file_list = ui.column().classes("w-full gap-2")
    selected: dict[str, bool] = {}
    progress_area = ui.column().classes("w-full gap-2")

    async def load_files() -> None:
        file_list.clear()
        files = await client.list_files()
        selected.clear()
        with file_list:
            for f in files:
                selected[f["id"]] = False
                cb = ui.checkbox(f"{f['name']}  ({f['size_human']})", value=False)

                def on_change(e, fid=f["id"]) -> None:
                    selected[fid] = e.value

                cb.on_value_change(on_change)

    async def do_download() -> None:
        ids = [fid for fid, on in selected.items() if on]
        if not ids:
            ui.notify("请选择文件", type="warning")
            return
        dest = Path(dest_input.value.strip())
        progress_area.clear()
        bars: dict[str, ui.linear_progress] = {}

        def on_progress(label: str, done: int, total: int) -> None:
            if label not in bars:
                with progress_area:
                    ui.label(label).classes("text-sm")
                    bars[label] = ui.linear_progress(value=0, show_value=False).classes("w-full")
            bars[label].value = done / total if total else 0

        try:
            await client.download_items(ids, dest, progress_callback=on_progress)
            ui.notify("下载完成", type="positive")
        except Exception as ex:
            ui.notify(str(ex), type="negative")

    ui.button("刷新列表", on_click=load_files).props("flat")
    ui.button("开始下载", on_click=do_download).props("unelevated color=primary")
    ui.timer(0.1, load_files, once=True)
