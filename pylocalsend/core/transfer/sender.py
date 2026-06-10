"""Sender HTTP service — registers paths and streams files."""

from __future__ import annotations

import secrets
import queue
import threading
import uuid
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from pylocalsend.core.file_handler.download_grants import filter_tree_entries, is_path_granted
from pylocalsend.core.file_handler.file_handler import (
    FileEntry,
    format_size,
    iter_files_recursive,
    list_dir_contents,
    relative_to_root,
    stat_path,
)
from pylocalsend.core.file_handler.streaming import async_read_chunks, parse_range_header
from pylocalsend.core.utils.config import AppConfig
from pylocalsend.core.utils.crypto import StreamCipher, derive_key
from pylocalsend.core.utils.db import Database
from pylocalsend.core.utils.logger import get_logger
from pylocalsend.core.utils.network import AccessUrls, get_access_urls

log = get_logger(__name__)


class UploadRequest(BaseModel):
    paths: list[str]


class ReceiverCreateRequest(BaseModel):
    name: str
    pin: str | None = None


class SenderService:
    """Core sender business logic shared by CLI and GUI."""

    def __init__(self, config: AppConfig | None = None, db: Database | None = None) -> None:
        self.config = config or AppConfig.load()
        self.db = db or Database()
        self.active_downloads: dict[str, int] = {}
        self.connections: set[str] = set()
        self._download_cancel: dict[int, threading.Event] = {}
        self._download_receiver: dict[int, str | None] = {}
        self.app = FastAPI(title="PyLocalSend Sender")
        self._mount_routes()

    @property
    def access_urls(self) -> AccessUrls:
        return get_access_urls(self.config.port, self.config.host)

    @property
    def base_url(self) -> str:
        return self.access_urls.primary

    def _cipher(self, file_id: str, pin: str) -> StreamCipher | None:
        if not self.config.encryption_enabled:
            return None
        return StreamCipher(derive_key(pin), file_id)

    def _auth(
        self,
        pin: str | None,
        token: str | None,
    ) -> tuple[str, str | None]:
        """Return (effective_pin, receiver_id)."""
        if token:
            receiver = self.db.get_receiver_by_token(token)
            if not receiver:
                raise HTTPException(403, "Invalid receiver token")
            return receiver["pin"], receiver["id"]
        if self.config.pin_verification_enabled:
            expected = self.config.server_pin
            if not expected:
                raise HTTPException(403, "Server PIN not configured")
            if pin != expected:
                raise HTTPException(403, "Invalid PIN")
            return expected, None
        return pin or "", None

    def _auth_download(
        self,
        pin: str | None,
        token: str | None,
    ) -> tuple[str, str | None]:
        """Authenticate for download; reject disabled receivers."""
        effective_pin, receiver_id = self._auth(pin, token)
        if receiver_id:
            receiver = self.db.get_receiver(receiver_id)
            if not receiver or receiver["status"] != "active":
                raise HTTPException(403, "Receiver is disabled")
        return effective_pin, receiver_id

    def _register_download(self, log_id: int, receiver_id: str | None) -> threading.Event:
        cancel = threading.Event()
        self._download_cancel[log_id] = cancel
        self._download_receiver[log_id] = receiver_id
        return cancel

    def _unregister_download(self, log_id: int) -> None:
        self._download_cancel.pop(log_id, None)
        self._download_receiver.pop(log_id, None)

    def disable_receiver(self, receiver_id: str) -> bool:
        if not self.db.disable_receiver(receiver_id):
            return False
        for log_id, rid in list(self._download_receiver.items()):
            if rid == receiver_id:
                self._download_cancel[log_id].set()
        return True

    def enable_receiver(self, receiver_id: str) -> bool:
        return self.db.enable_receiver(receiver_id)

    def get_download_grants(self, file_id: str) -> set[str]:
        return self.db.get_download_grants(file_id)

    def set_download_grants(self, file_id: str, relative_paths: set[str]) -> None:
        self.db.set_download_grants(file_id, relative_paths)

    def _list_downloadable_files(self) -> list[dict[str, Any]]:
        return [
            f for f in self.db.list_files()
            if self.db.has_download_grants(f["id"])
        ]

    def _ensure_download_allowed(self, file_id: str, relative: str | None) -> None:
        grants = self.db.get_download_grants(file_id)
        rel = relative or ""
        if not is_path_granted(rel, grants):
            raise HTTPException(403, "Download not allowed")

    def _mount_routes(self) -> None:
        svc = self

        async def require_auth(
            x_pin: str | None = Header(default=None, alias="X-PIN"),
            x_token: str | None = Header(default=None, alias="X-Token"),
        ) -> tuple[str, str | None]:
            return svc._auth(x_pin, x_token)

        @self.app.post("/api/shutdown")
        async def shutdown(
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> dict:
            import os
            import threading

            def _exit() -> None:
                os._exit(0)

            threading.Timer(0.3, _exit).start()
            return {"ok": True}

        @self.app.get("/api/status")
        async def status(auth: tuple[str, str | None] = Depends(require_auth)) -> dict:
            svc.connections.add(auth[0][:8])
            files = svc.db.list_files()
            urls = svc.access_urls
            return {
                "connections": len(svc.connections),
                "files_count": len(files),
                "active_downloads": len(svc.active_downloads),
                "encryption_enabled": svc.config.encryption_enabled,
                "pin_verification_enabled": svc.config.pin_verification_enabled,
                "host": svc.config.host,
                "port": svc.config.port,
                "base_url": urls.primary,
                "access_urls": {label: url for label, url in urls.labels()},
            }

        @self.app.get("/api/files")
        async def list_files(auth: tuple[str, str | None] = Depends(require_auth)) -> list[dict]:
            records = svc._list_downloadable_files() if auth[1] else svc.db.list_files()
            return [_file_to_api(f) for f in records]

        @self.app.get("/api/files/catalog-version")
        async def catalog_version(auth: tuple[str, str | None] = Depends(require_auth)) -> dict:
            return {"version": svc.db.get_download_catalog_version()}

        @self.app.post("/api/files")
        async def register_files(
            body: UploadRequest,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> list[dict]:
            added = []
            for raw in body.paths:
                try:
                    entry = svc.register_path(raw)
                    added.append(_file_to_api(entry))
                except (FileNotFoundError, OSError) as e:
                    log.warning("Skip %s: %s", raw, e)
            return added

        @self.app.delete("/api/files/{file_id}")
        async def delete_file(
            file_id: str,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> dict:
            if not svc.db.remove_file_by_id(file_id):
                raise HTTPException(404, "File not found")
            return {"ok": True}

        @self.app.get("/api/files/{file_id}/contents")
        async def folder_contents(
            file_id: str,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> list[dict]:
            record = svc.db.get_file(file_id)
            if not record:
                raise HTTPException(404, "Not found")
            if not record["is_dir"]:
                raise HTTPException(400, "Not a directory")
            return list_dir_contents(Path(record["path"]))

        @self.app.get("/api/files/{file_id}/tree")
        async def file_tree(
            file_id: str,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> list[dict]:
            record = svc.db.get_file(file_id)
            if not record:
                raise HTTPException(404, "Not found")
            grants = svc.db.get_download_grants(file_id)
            if auth[1] and not grants:
                raise HTTPException(404, "Not found")
            root = Path(record["path"])
            if root.is_file():
                items = [
                    {
                        "relative_path": record["name"],
                        "size": record["size"],
                        "file_id": file_id,
                    }
                ]
            else:
                items = []
                for fp, size in iter_files_recursive(root):
                    items.append(
                        {
                            "relative_path": relative_to_root(fp, root),
                            "size": size,
                            "absolute_path": str(fp),
                        }
                    )
            if auth[1]:
                items = filter_tree_entries(items, grants)
            return items

        @self.app.get("/api/files/{file_id}/downloads")
        async def file_downloads(
            file_id: str,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> list[dict]:
            return svc.db.list_downloads_for_file(file_id)

        @self.app.get("/api/download/{file_id}")
        async def download_file(
            file_id: str,
            request: Request,
            relative: str | None = None,
            pin: str | None = None,
            token: str | None = None,
            browser: bool = False,
            x_pin: str | None = Header(default=None, alias="X-PIN"),
            x_token: str | None = Header(default=None, alias="X-Token"),
        ) -> StreamingResponse:
            pin, receiver_id = svc._auth_download(x_pin or pin, x_token or token)
            record = svc.db.get_file(file_id)
            if not record:
                raise HTTPException(404, "Not found")

            root = Path(record["path"])
            if record["is_dir"]:
                if not relative:
                    raise HTTPException(400, "relative path required for directory entries")
                file_path = (root / relative).resolve()
                if not str(file_path).startswith(str(root.resolve())):
                    raise HTTPException(403, "Path traversal denied")
            else:
                file_path = root

            svc._ensure_download_allowed(file_id, relative)

            if not file_path.is_file():
                raise HTTPException(404, "File not found on disk")

            file_size = file_path.stat().st_size
            start, end = parse_range_header(request.headers.get("range"), file_size)
            length = end - start + 1
            cipher = None if browser else svc._cipher(file_id, pin)
            downloader = request.headers.get("X-Downloader", "browser" if browser else "anonymous")
            log_id = svc.db.log_download_start(file_id, downloader, receiver_id)
            cancel = svc._register_download(log_id, receiver_id)
            svc.active_downloads[file_id] = svc.active_downloads.get(file_id, 0) + 1

            async def stream():
                sent = 0
                try:
                    async for chunk in async_read_chunks(
                        file_path,
                        svc.config.chunk_size,
                        start=start,
                        length=length,
                        cipher=cipher,
                    ):
                        if cancel.is_set():
                            svc.db.log_download_finish(log_id, "cancelled", sent)
                            return
                        sent += len(chunk)
                        yield chunk
                    if cancel.is_set():
                        svc.db.log_download_finish(log_id, "cancelled", sent)
                        return
                    svc.db.log_download_finish(log_id, "completed", sent)
                except Exception:
                    status = "cancelled" if cancel.is_set() else "failed"
                    svc.db.log_download_finish(log_id, status, sent)
                    if not cancel.is_set():
                        raise
                finally:
                    svc._unregister_download(log_id)
                    svc.active_downloads[file_id] = max(
                        0, svc.active_downloads.get(file_id, 1) - 1
                    )

            headers = {
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'attachment; filename="{file_path.name}"',
                "X-Encrypted": "1" if cipher else "0",
            }
            if request.headers.get("range"):
                headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
                return StreamingResponse(
                    stream(),
                    status_code=206,
                    media_type="application/octet-stream",
                    headers=headers,
                )
            return StreamingResponse(
                stream(),
                media_type="application/octet-stream",
                headers=headers,
            )

        @self.app.get("/api/download/{file_id}/zip")
        async def download_directory_zip(
            file_id: str,
            request: Request,
            pin: str | None = None,
            token: str | None = None,
            x_pin: str | None = Header(default=None, alias="X-PIN"),
            x_token: str | None = Header(default=None, alias="X-Token"),
        ) -> StreamingResponse:
            _pin, receiver_id = svc._auth_download(x_pin or pin, x_token or token)
            record = svc.db.get_file(file_id)
            if not record:
                raise HTTPException(404, "Not found")
            if not record["is_dir"]:
                raise HTTPException(400, "ZIP download is only available for directories")

            root = Path(record["path"]).resolve()
            if not root.is_dir():
                raise HTTPException(404, "Directory not found on disk")

            grants = svc.db.get_download_grants(file_id)
            if not grants:
                raise HTTPException(403, "Download not allowed")

            downloader = request.headers.get("X-Downloader", "browser")
            log_id = svc.db.log_download_start(file_id, downloader, receiver_id)
            cancel = svc._register_download(log_id, receiver_id)
            svc.active_downloads[file_id] = svc.active_downloads.get(file_id, 0) + 1

            def stream() -> Iterator[bytes]:
                sent = 0
                try:
                    for chunk in _stream_directory_zip(
                        root,
                        str(record["name"]),
                        svc.config.chunk_size,
                        grants=grants,
                    ):
                        if cancel.is_set():
                            svc.db.log_download_finish(log_id, "cancelled", sent)
                            return
                        sent += len(chunk)
                        yield chunk
                    if cancel.is_set():
                        svc.db.log_download_finish(log_id, "cancelled", sent)
                        return
                    svc.db.log_download_finish(log_id, "completed", sent)
                except Exception:
                    status = "cancelled" if cancel.is_set() else "failed"
                    svc.db.log_download_finish(log_id, status, sent)
                    if not cancel.is_set():
                        raise
                finally:
                    svc._unregister_download(log_id)
                    svc.active_downloads[file_id] = max(
                        0, svc.active_downloads.get(file_id, 1) - 1
                    )

            headers = {
                "Content-Disposition": f'attachment; filename="{record["name"]}.zip"',
                "X-Encrypted": "0",
            }
            return StreamingResponse(
                stream(),
                media_type="application/zip",
                headers=headers,
            )

        @self.app.get("/api/receivers")
        async def list_receivers(
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> list[dict]:
            return [_receiver_to_api(r, svc.base_url) for r in svc.db.list_receivers()]

        @self.app.post("/api/receivers")
        async def create_receiver(
            body: ReceiverCreateRequest,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> dict:
            from pylocalsend.core.utils.crypto import generate_pin

            pin = body.pin or generate_pin()
            receiver_id = str(uuid.uuid4())
            token = secrets.token_urlsafe(16)
            self.db.add_receiver(receiver_id, body.name, pin, token)
            record = self.db.get_receiver(receiver_id)
            return _receiver_to_api(record, svc.base_url)

        @self.app.delete("/api/receivers/{receiver_id}")
        async def delete_receiver(
            receiver_id: str,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> dict:
            if not svc.db.remove_receiver(receiver_id):
                raise HTTPException(404, "Receiver not found")
            return {"ok": True}

        @self.app.post("/api/receivers/{receiver_id}/disable")
        async def disable_receiver(
            receiver_id: str,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> dict:
            if not svc.disable_receiver(receiver_id):
                raise HTTPException(404, "Receiver not found or already disabled")
            return {"ok": True}

        @self.app.post("/api/receivers/{receiver_id}/enable")
        async def enable_receiver(
            receiver_id: str,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> dict:
            if not svc.enable_receiver(receiver_id):
                raise HTTPException(404, "Receiver not found or not disabled")
            return {"ok": True}

        @self.app.get("/api/receivers/{receiver_id}/downloads")
        async def receiver_downloads(
            receiver_id: str,
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> list[dict]:
            return svc.db.list_downloads_for_receiver(receiver_id)

        @self.app.get("/api/config")
        async def get_config(
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> dict:
            return svc.config.as_display_dict()

        @self.app.put("/api/config")
        async def update_config(
            body: dict[str, Any],
            auth: tuple[str, str | None] = Depends(require_auth),
        ) -> dict:
            for key, value in body.items():
                if hasattr(svc.config, key):
                    svc.config.set(key, value)
            return svc.config.as_display_dict()

    def register_path(self, raw_path: str) -> dict[str, Any]:
        entry = stat_path(Path(raw_path))
        existing = self.db.get_file_by_path(str(entry.path))
        file_id = existing["id"] if existing else entry.id
        self.db.add_file(
            file_id,
            str(entry.path),
            entry.name,
            entry.is_dir,
            entry.size,
            entry.mtime,
        )
        return self.db.get_file(file_id)  # type: ignore[return-value]

    def remove_path(self, raw_path: str) -> bool:
        path = str(Path(raw_path).resolve())
        return self.db.remove_file_by_path(path)

    def list_files_local(self) -> list[dict[str, Any]]:
        return [_file_to_api(f) for f in self.db.list_files()]

    def create_receiver(self, name: str, pin: str | None = None) -> dict[str, Any]:
        from pylocalsend.core.utils.crypto import generate_pin

        pin = pin or generate_pin()
        receiver_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(16)
        self.db.add_receiver(receiver_id, name, pin, token)
        return _receiver_to_api(self.db.get_receiver(receiver_id), self.base_url)

    def get_status_local(self) -> dict[str, Any]:
        urls = self.access_urls
        return {
            "running": True,
            "connections": len(self.connections),
            "files_count": len(self.db.list_files()),
            "active_downloads": len(self.active_downloads),
            "base_url": urls.primary,
            "access_urls": {label: url for label, url in urls.labels()},
        }


def _file_to_api(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "path": record["path"],
        "name": record["name"],
        "is_dir": bool(record["is_dir"]),
        "size": record["size"],
        "size_human": format_size(record["size"]),
        "mtime": record["mtime"],
        "uploaded_at": record["uploaded_at"],
        "status": record["status"],
    }


def _receiver_to_api(record: dict[str, Any] | None, base_url: str) -> dict[str, Any]:
    if not record:
        return {}
    link = f"{base_url}/r/{record['token']}"
    return {
        "id": record["id"],
        "name": record["name"],
        "pin": record["pin"],
        "token": record["token"],
        "link": link,
        "status": record["status"],
        "created_at": record["created_at"],
    }


def _stream_directory_zip(
    root: Path,
    root_name: str,
    chunk_size: int,
    *,
    grants: set[str] | None = None,
) -> Iterator[bytes]:
    """Stream a folder as ZIP without first writing the archive to disk."""
    chunks: queue.Queue[bytes | BaseException | None] = queue.Queue(maxsize=8)

    class QueueWriter:
        def write(self, data: bytes) -> int:
            if data:
                chunks.put(bytes(data))
            return len(data)

        def flush(self) -> None:
            return None

    def produce() -> None:
        try:
            with zipfile.ZipFile(
                QueueWriter(),
                mode="w",
                compression=zipfile.ZIP_STORED,
                allowZip64=True,
            ) as archive:
                for file_path, _size in iter_files_recursive(root):
                    arcname = f"{root_name}/{relative_to_root(file_path, root)}"
                    rel = relative_to_root(file_path, root)
                    if grants is not None and not is_path_granted(rel, grants):
                        continue
                    with archive.open(arcname, "w", force_zip64=True) as zip_entry:
                        with file_path.open("rb") as source:
                            while data := source.read(chunk_size):
                                zip_entry.write(data)
        except BaseException as ex:
            chunks.put(ex)
        finally:
            chunks.put(None)

    threading.Thread(target=produce, daemon=True).start()

    while True:
        item = chunks.get()
        if item is None:
            break
        if isinstance(item, BaseException):
            raise item
        yield item
