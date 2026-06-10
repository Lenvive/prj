"""Tests for sender WebUI auth helpers."""

from __future__ import annotations

import io
from contextlib import redirect_stdout

from pylocalsend.core.utils.config import AppConfig
from pylocalsend.core.utils.network import AccessUrls
from pylocalsend.gui.sender.auth import (
    ensure_gui_auth_config,
    print_startup_access_info,
    sender_url_with_pin,
    verify_pin,
)


def test_verify_pin() -> None:
    cfg = AppConfig(server_pin="123456")
    assert verify_pin("123456", cfg) is True
    assert verify_pin("000000", cfg) is False
    assert verify_pin("", cfg) is False


def test_ensure_gui_auth_config_generates_pin_and_enables_verification() -> None:
    cfg = AppConfig(server_pin="", pin_verification_enabled=False)
    cfg.save = lambda: None  # type: ignore[method-assign]
    ensure_gui_auth_config(cfg)
    assert cfg.server_pin
    assert len(cfg.server_pin) == 6
    assert cfg.pin_verification_enabled is True


def test_sender_url_with_pin() -> None:
    assert sender_url_with_pin("http://127.0.0.1:8765", "654321") == (
        "http://127.0.0.1:8765/?pin=654321"
    )
    assert sender_url_with_pin("http://127.0.0.1:8765/", "654321") == (
        "http://127.0.0.1:8765/?pin=654321"
    )


def test_print_startup_access_info() -> None:
    cfg = AppConfig(server_pin="112233")
    urls = AccessUrls(
        bind_host="0.0.0.0",
        port=8765,
        localhost="http://127.0.0.1:8765",
        lan=["http://192.168.1.10:8765"],
        public=None,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        print_startup_access_info(cfg, urls)
    text = buf.getvalue()
    assert "访问地址（本机）: http://127.0.0.1:8765/" in text
    assert "密码: 112233" in text
    assert "直达链接: http://127.0.0.1:8765/?pin=112233" in text
    assert "访问地址（局域网）: http://192.168.1.10:8765/" in text
    assert "直达链接: http://192.168.1.10:8765/?pin=112233" in text
