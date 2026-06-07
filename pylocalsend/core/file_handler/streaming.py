"""Chunked streaming read/write with optional encryption."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator, Iterator

import aiofiles

from pylocalsend.core.utils.crypto import StreamCipher


def read_chunks(
    path: Path,
    chunk_size: int,
    start: int = 0,
    length: int | None = None,
    cipher: StreamCipher | None = None,
) -> Iterator[bytes]:
    file_size = path.stat().st_size
    end = file_size if length is None else min(start + length, file_size)
    if start >= end:
        return
    with path.open("rb") as f:
        f.seek(start)
        remaining = end - start
        offset = start
        while remaining > 0:
            to_read = min(chunk_size, remaining)
            data = f.read(to_read)
            if not data:
                break
            if cipher:
                data = cipher.encrypt(data, offset)
            yield data
            offset += len(data) if cipher else len(data)
            remaining -= to_read


async def async_read_chunks(
    path: Path,
    chunk_size: int,
    start: int = 0,
    length: int | None = None,
    cipher: StreamCipher | None = None,
) -> AsyncIterator[bytes]:
    file_size = path.stat().st_size
    end = file_size if length is None else min(start + length, file_size)
    if start >= end:
        return
    async with aiofiles.open(path, "rb") as f:
        await f.seek(start)
        remaining = end - start
        offset = start
        while remaining > 0:
            to_read = min(chunk_size, remaining)
            data = await f.read(to_read)
            if not data:
                break
            if cipher:
                data = cipher.encrypt(data, offset)
            yield data
            offset += to_read
            remaining -= to_read


async def write_stream(
    dest: Path,
    chunks: AsyncIterator[bytes],
    append: bool = False,
    cipher: StreamCipher | None = None,
    start_offset: int = 0,
) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    mode = "ab" if append else "wb"
    written = 0
    offset = start_offset
    async with aiofiles.open(dest, mode) as f:
        if append and start_offset:
            await f.seek(start_offset)
        async for chunk in chunks:
            if cipher:
                chunk = cipher.decrypt(chunk, offset)
            await f.write(chunk)
            written += len(chunk)
            offset += len(chunk)
    return written


def parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int]:
    """Return (start, end) inclusive byte range."""
    if not range_header or not range_header.startswith("bytes="):
        return 0, file_size - 1
    spec = range_header.split("=", 1)[1].strip()
    if "," in spec:
        spec = spec.split(",", 1)[0]
    start_s, end_s = spec.split("-", 1)
    if start_s:
        start = int(start_s)
        end = int(end_s) if end_s else file_size - 1
    else:
        suffix = int(end_s)
        start = max(0, file_size - suffix)
        end = file_size - 1
    end = min(end, file_size - 1)
    return start, end
