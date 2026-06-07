"""Sender server lifecycle (singleton)."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import uvicorn

from pylocalsend.core.transfer.sender import SenderService
from pylocalsend.core.utils.config import AppConfig
from pylocalsend.core.utils.logger import get_logger
from pylocalsend.core.utils.port import find_free_port

if TYPE_CHECKING:
    from uvicorn import Server

log = get_logger(__name__)

_server: Server | None = None
_thread: threading.Thread | None = None
_service: SenderService | None = None
_gui_mode: bool = False


def get_service() -> SenderService:
    global _service
    if _service is None:
        _service = SenderService()
    return _service


def is_running() -> bool:
    if _gui_mode and _service is not None:
        return True
    return _server is not None and _thread is not None and _thread.is_alive()


def prepare_service(config: AppConfig | None = None) -> SenderService:
    """Create sender service for GUI (uvicorn started by NiceGUI)."""
    global _service, _gui_mode
    cfg = config or AppConfig.load()
    _service = SenderService(cfg)
    _gui_mode = True
    return _service


def start_server(config: AppConfig | None = None, open_browser: bool = False) -> SenderService:
    global _server, _thread, _service
    if is_running():
        return get_service()

    cfg = config or AppConfig.load()
    if cfg.port == 0 or _port_in_use(cfg.host, cfg.port):
        cfg.port = find_free_port("127.0.0.1", cfg.port if cfg.port else 8765)
        cfg.save()

    _service = SenderService(cfg)
    uv_config = uvicorn.Config(
        _service.app,
        host=cfg.host,
        port=cfg.port,
        log_level="warning",
    )
    _server = uvicorn.Server(uv_config)

    def run() -> None:
        _server.run()

    _thread = threading.Thread(target=run, daemon=True)
    _thread.start()
    log.info("Sender started at %s", _service.base_url)

    if open_browser:
        import webbrowser

        webbrowser.open(_service.base_url)

    return _service


def stop_server() -> None:
    global _server, _thread, _service, _gui_mode
    if _server is not None:
        _server.should_exit = True
    if _thread is not None:
        _thread.join(timeout=5)
    _server = None
    _thread = None
    _service = None
    _gui_mode = False
    log.info("Sender stopped")


def _port_in_use(host: str, port: int) -> bool:
    import socket

    bind_host = "127.0.0.1" if host == "0.0.0.0" else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((bind_host, port)) == 0
