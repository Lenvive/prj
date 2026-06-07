"""Stream encryption using AES-CTR (seek-friendly for resume)."""

from __future__ import annotations

import hashlib
import secrets
from typing import Iterator

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def generate_pin(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def derive_key(pin: str, salt: bytes = b"pylocalsend-v1") -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 120_000, dklen=32)


def _counter_for_offset(file_id: str, byte_offset: int, block_size: int = 16) -> bytes:
    block_index = byte_offset // block_size
    seed = f"{file_id}:{block_index}".encode()
    return hashlib.sha256(seed).digest()[:16]


class StreamCipher:
    """AES-CTR cipher tied to a file id for random access."""

    def __init__(self, key: bytes, file_id: str) -> None:
        self._key = key
        self._file_id = file_id

    def encrypt(self, data: bytes, offset: int) -> bytes:
        if not data:
            return data
        nonce = _counter_for_offset(self._file_id, offset)
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CTR(nonce),
            backend=default_backend(),
        )
        return cipher.encryptor().update(data)

    def decrypt(self, data: bytes, offset: int) -> bytes:
        return self.encrypt(data, offset)


def encrypt_chunks(
    cipher: StreamCipher,
    chunks: Iterator[tuple[int, bytes]],
) -> Iterator[tuple[int, bytes]]:
    for offset, chunk in chunks:
        yield offset, cipher.encrypt(chunk, offset)
