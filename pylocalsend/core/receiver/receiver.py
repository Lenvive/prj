"""Receiver client — list and download with resume and parallelism."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

import httpx

from pylocalsend.core.utils.crypto import StreamCipher, derive_key
from pylocalsend.core.utils.logger import get_logger

log = get_logger(__name__)


class ReceiverClient:
    def __init__(
        self,
        host: str,
        pin: str,
        token: str | None = None,
        max_parallel: int = 4,
        chunk_size: int = 8 * 1024 * 1024,
    ) -> None:
        self.host = host.rstrip("/")
        self.pin = pin
        self.token = token
        self.max_parallel = max_parallel
        self.chunk_size = chunk_size
        self._headers = self._build_headers()

    def _build_headers(self) -> dict[str, str]:
        h: dict[str, str] = {"X-PIN": self.pin, "X-Downloader": "cli"}
        if self.token:
            h["X-Token"] = self.token
        return h

    async def list_files(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.host}/api/files", headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def get_status(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{self.host}/api/status", headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def get_tree(self, file_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(
                f"{self.host}/api/files/{file_id}/tree",
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()

    async def download_items(
        self,
        names_or_ids: list[str],
        dest_dir: Path,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> list[Path]:
        files = await self.list_files()
        by_name = {f["name"]: f for f in files}
        by_id = {f["id"]: f for f in files}

        jobs: list[tuple[str, str, str, Path]] = []
        for item in names_or_ids:
            record = by_id.get(item) or by_name.get(item)
            if not record:
                log.warning("Unknown item: %s", item)
                continue
            if record["is_dir"]:
                tree = await self.get_tree(record["id"])
                for entry in tree:
                    rel = entry["relative_path"]
                    out = dest_dir / record["name"] / rel
                    jobs.append((record["id"], rel, record["name"], out))
            else:
                jobs.append((record["id"], "", record["name"], dest_dir / record["name"]))

        sem = asyncio.Semaphore(self.max_parallel)

        async def one(job: tuple[str, str, str, Path]) -> Path:
            file_id, relative, _name, out_path = job
            async with sem:
                return await self._download_file(
                    file_id, relative, out_path, progress_callback
                )

        return await asyncio.gather(*[one(j) for j in jobs])

    async def _download_file(
        self,
        file_id: str,
        relative: str,
        dest: Path,
        progress_callback: Callable[[str, int, int], None] | None,
    ) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        label = relative or dest.name
        existing = dest.stat().st_size if dest.exists() else 0

        params = {"relative": relative} if relative else {}
        headers = dict(self._headers)
        if existing:
            headers["Range"] = f"bytes={existing}-"

        encrypted = False
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET",
                f"{self.host}/api/download/{file_id}",
                headers=headers,
                params=params,
            ) as resp:
                resp.raise_for_status()
                encrypted = resp.headers.get("X-Encrypted") == "1"
                total_header = resp.headers.get("Content-Length")
                total = int(total_header) + existing if total_header else None
                if progress_callback and total:
                    progress_callback(label, existing, total)

                cipher = (
                    StreamCipher(derive_key(self.pin), file_id) if encrypted else None
                )
                mode = "ab" if existing else "wb"
                written = existing
                offset = existing
                with dest.open(mode) as f:
                    async for chunk in resp.aiter_bytes(self.chunk_size):
                        if cipher:
                            chunk = cipher.decrypt(chunk, offset)
                        f.write(chunk)
                        written += len(chunk)
                        offset += len(chunk)
                        if progress_callback and total:
                            progress_callback(label, written, total)

        if progress_callback and total:
            progress_callback(label, written, total or written)
        return dest


def list_files_sync(host: str, pin: str, token: str | None = None) -> list[dict]:
    return asyncio.run(ReceiverClient(host, pin, token).list_files())


def download_sync(
    host: str,
    pin: str,
    items: list[str],
    dest: Path,
    max_parallel: int = 4,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> list[Path]:
    client = ReceiverClient(host, pin, max_parallel=max_parallel)
    return asyncio.run(client.download_items(items, dest, progress_callback))
