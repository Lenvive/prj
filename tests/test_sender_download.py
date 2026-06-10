from __future__ import annotations

import asyncio
import io
import zipfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from pylocalsend.core.transfer.sender import SenderService
from pylocalsend.core.utils import config as config_mod
from pylocalsend.core.utils import db as db_mod
from pylocalsend.core.utils.config import AppConfig
from pylocalsend.core.utils.db import Database


@pytest.fixture(autouse=True)
def isolated_app_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_dir = tmp_path / "app"
    monkeypatch.setattr(config_mod, "APP_DIR", app_dir)
    monkeypatch.setattr(config_mod, "CONFIG_PATH", app_dir / "config.json")
    monkeypatch.setattr(config_mod, "SESSION_PATH", app_dir / "session.json")
    monkeypatch.setattr(db_mod, "APP_DIR", app_dir)


def _service(tmp_path: Path) -> SenderService:
    cfg = AppConfig(
        encryption_enabled=True,
        pin_verification_enabled=True,
        server_pin="123456",
        chunk_size=4,
    )
    return SenderService(cfg, Database(tmp_path / "pylocalsend.db"))


def test_browser_download_query_token_streams_plaintext(tmp_path: Path) -> None:
    shared = tmp_path / "hello.txt"
    shared.write_bytes(b"hello receiver")
    svc = _service(tmp_path)
    record = svc.register_path(str(shared))
    receiver = svc.create_receiver("laptop", "654321")

    response = TestClient(svc.app).get(
        f"/api/download/{record['id']}",
        params={"token": receiver["token"], "browser": "1"},
    )

    assert response.status_code == 200
    assert response.content == b"hello receiver"
    assert response.headers["x-encrypted"] == "0"
    logs = svc.db.list_downloads_for_file(record["id"])
    assert logs[0]["downloader"] == "browser"
    assert logs[0]["receiver_id"] == receiver["id"]


def test_directory_browser_download_streams_zip(tmp_path: Path) -> None:
    shared_dir = tmp_path / "shared"
    nested = shared_dir / "nested"
    nested.mkdir(parents=True)
    (shared_dir / "a.txt").write_text("a", encoding="utf-8")
    (nested / "b.txt").write_text("b", encoding="utf-8")
    svc = _service(tmp_path)
    record = svc.register_path(str(shared_dir))
    receiver = svc.create_receiver("laptop", "654321")

    response = TestClient(svc.app).get(
        f"/api/download/{record['id']}/zip",
        params={"token": receiver["token"]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert sorted(archive.namelist()) == ["shared/a.txt", "shared/nested/b.txt"]
        assert archive.read("shared/a.txt") == b"a"
        assert archive.read("shared/nested/b.txt") == b"b"


def test_disable_receiver_blocks_new_download(tmp_path: Path) -> None:
    shared = tmp_path / "hello.txt"
    shared.write_bytes(b"hello receiver")
    svc = _service(tmp_path)
    record = svc.register_path(str(shared))
    receiver = svc.create_receiver("laptop", "654321")
    client = TestClient(svc.app)

    assert svc.disable_receiver(receiver["id"]) is True

    response = client.get(
        f"/api/download/{record['id']}",
        params={"token": receiver["token"], "browser": "1"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_disable_receiver_cancels_active_download(tmp_path: Path) -> None:
    shared = tmp_path / "large.bin"
    shared.write_bytes(b"x" * 64)
    cfg = AppConfig(
        encryption_enabled=True,
        pin_verification_enabled=True,
        server_pin="123456",
        chunk_size=4,
    )
    svc = SenderService(cfg, Database(tmp_path / "pylocalsend.db"))
    record = svc.register_path(str(shared))
    receiver = svc.create_receiver("laptop", "654321")

    transport = httpx.ASGITransport(app=svc.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        download = asyncio.create_task(
            client.get(
                f"/api/download/{record['id']}",
                params={"token": receiver["token"], "browser": "1"},
            )
        )
        for _ in range(100):
            if svc._download_cancel or download.done():
                break
            await asyncio.sleep(0)

        assert svc._download_cancel
        assert svc.disable_receiver(receiver["id"]) is True
        response = await download

        assert response.status_code == 200
        assert len(response.content) < 64

    logs = svc.db.list_downloads_for_receiver(receiver["id"])
    assert logs[0]["status"] == "cancelled"


def test_enable_receiver_restores_download(tmp_path: Path) -> None:
    shared = tmp_path / "hello.txt"
    shared.write_bytes(b"hello receiver")
    svc = _service(tmp_path)
    record = svc.register_path(str(shared))
    receiver = svc.create_receiver("laptop", "654321")
    client = TestClient(svc.app)

    assert svc.disable_receiver(receiver["id"]) is True
    blocked = client.get(
        f"/api/download/{record['id']}",
        params={"token": receiver["token"], "browser": "1"},
    )
    assert blocked.status_code == 403

    assert svc.enable_receiver(receiver["id"]) is True
    response = client.get(
        f"/api/download/{record['id']}",
        params={"token": receiver["token"], "browser": "1"},
    )
    assert response.status_code == 200
    assert response.content == b"hello receiver"
