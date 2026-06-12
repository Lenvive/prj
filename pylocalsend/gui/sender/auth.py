"""Sender WebUI PIN login."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from urllib.parse import urlencode

from nicegui import app, ui

from pylocalsend.core.utils.config import AppConfig
from pylocalsend.core.utils.crypto import generate_pin
from pylocalsend.core.utils.network import AccessUrls

AUTH_SESSION_KEY = "sender_pin"


def ensure_gui_auth_config(cfg: AppConfig) -> None:
    """Ensure sender WebUI and API both require a server PIN."""
    changed = False
    if not cfg.server_pin:
        cfg.server_pin = generate_pin()
        changed = True
    if not cfg.pin_verification_enabled:
        cfg.pin_verification_enabled = True
        changed = True
    if changed:
        cfg.save()


def verify_pin(pin: str, cfg: AppConfig) -> bool:
    return bool(cfg.server_pin) and pin == cfg.server_pin


def is_authenticated(cfg: AppConfig) -> bool:
    return app.storage.user.get(AUTH_SESSION_KEY) == cfg.server_pin


def mark_authenticated(cfg: AppConfig) -> None:
    app.storage.user[AUTH_SESSION_KEY] = cfg.server_pin


def sender_url_with_pin(base_url: str, pin: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/?{urlencode({'pin': pin})}"


def gui_storage_secret(cfg: AppConfig) -> str:
    material = cfg.server_pin or "pylocalsend-gui"
    return hashlib.sha256(f"pylocalsend-gui:{material}".encode()).hexdigest()


def print_startup_access_info(cfg: AppConfig, access_urls: AccessUrls) -> None:
    pin = cfg.server_pin
    print("\nPyLocalSend 发送端 WebUI\n")
    for label, url in access_urls.labels():
        print(f"访问地址（{label}）: {url}/")
        print(f"密码: {pin}")
        print(f"直达链接: {sender_url_with_pin(url, pin)}")
        print()
    if access_urls.public:
        print("公网地址需路由器端口映射后才可从外网访问\n")


def render_login_page(cfg: AppConfig, style: str, *, error: str | None = None) -> None:
    ui.add_head_html(style)
    with ui.column().classes("w-full max-w-md mx-auto p-8 gap-4"):
        ui.label("PyLocalSend").classes("page-title")
        ui.label("请输入发送端密码以登录管理界面").classes("muted")
        if error:
            ui.label(error).classes("text-negative text-sm")
        pin_input = ui.input("密码", password=True).props("outlined dense")

        def attempt_login() -> None:
            if verify_pin(pin_input.value, cfg):
                mark_authenticated(cfg)
                ui.navigate.to("/")
            else:
                ui.notify("密码错误", type="negative")

        pin_input.on("keydown.enter", attempt_login)
        ui.button("登录", on_click=attempt_login).props("unelevated color=primary")


def guard_sender_page(cfg: AppConfig, style: str, build_page: Callable[[], None]) -> None:
    query_pin = ui.context.client.request.query_params.get("pin")
    if query_pin is not None:
        if verify_pin(query_pin, cfg):
            mark_authenticated(cfg)
            ui.navigate.to("/")
            return
        render_login_page(cfg, style, error="链接中的密码无效，请重新输入")
        return

    if is_authenticated(cfg):
        build_page()
        return

    render_login_page(cfg, style)
