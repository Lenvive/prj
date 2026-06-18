"""Network address helpers for local access and sharing."""

from __future__ import annotations

import re
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_PUBLIC_IP_UNSET = object()
_PUBLIC_IP: str | None | object = _PUBLIC_IP_UNSET


@dataclass(frozen=True)
class AccessUrls:
    bind_host: str
    port: int
    localhost: str
    lan: list[str]
    public: str | None

    @property
    def primary(self) -> str:
        if self.lan:
            return self.lan[0]
        return self.localhost

    def labels(self) -> list[tuple[str, str]]:
        items = [("本机", self.localhost)]
        for index, url in enumerate(self.lan):
            label = "局域网" if index == 0 else f"局域网 {index + 1}"
            items.append((label, url))
        if self.public:
            items.append(("公网", self.public))
        return items


def connect_host(bind_host: str) -> str:
    """Host to use when connecting to a service bound on all interfaces."""
    if bind_host in ("0.0.0.0", ""):
        return "127.0.0.1"
    return bind_host


def get_local_ips() -> list[str]:
    """Return non-loopback IPv4 addresses on this machine."""
    seen: set[str] = set()
    ips: list[str] = []

    def add(ip: str) -> None:
        if ip.startswith("127.") or ip == "0.0.0.0":
            return
        if ip not in seen:
            seen.add(ip)
            ips.append(ip)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            add(sock.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass

    if sys.platform == "win32":
        try:
            output = subprocess.check_output(
                ["ipconfig"],
                text=True,
                encoding="utf-8",
                errors="ignore",
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            for line in output.splitlines():
                if "IPv4" in line or "IP Address" in line:
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                    if match:
                        add(match.group(1))
        except (OSError, subprocess.SubprocessError):
            pass
    elif sys.platform == "darwin":
        try:
            output = subprocess.check_output(
                ["ifconfig"],
                text=True,
                encoding="utf-8",
                errors="ignore",
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            for match in re.finditer(
                r"^\s*inet\s+(\d+\.\d+\.\d+\.\d+)\b",
                output,
                re.MULTILINE,
            ):
                add(match.group(1))
        except (OSError, subprocess.SubprocessError):
            pass
    elif sys.platform.startswith("linux"):
        try:
            output = subprocess.check_output(
                ["hostname", "-I"],
                text=True,
                encoding="utf-8",
                errors="ignore",
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            for ip in output.split():
                add(ip.strip())
        except (OSError, subprocess.SubprocessError):
            pass

    return ips


def get_public_ip(timeout: float = 2.0, use_cache: bool = True) -> str | None:
    """Best-effort public IPv4 lookup."""
    global _PUBLIC_IP
    if use_cache and _PUBLIC_IP is not _PUBLIC_IP_UNSET:
        return _PUBLIC_IP  # type: ignore[return-value]

    ip: str | None = None
    try:
        import httpx

        response = httpx.get("https://api.ipify.org", timeout=timeout)
        if response.status_code == 200:
            candidate = response.text.strip()
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", candidate):
                ip = candidate
    except Exception:
        ip = None

    if use_cache:
        _PUBLIC_IP = ip
    return ip


def get_access_urls(port: int, bind_host: str = "0.0.0.0", *, include_public: bool = True) -> AccessUrls:
    localhost = f"http://127.0.0.1:{port}"

    if bind_host not in ("0.0.0.0", ""):
        configured = f"http://{bind_host}:{port}"
        lan = [] if bind_host == "127.0.0.1" else [configured]
        return AccessUrls(
            bind_host=bind_host,
            port=port,
            localhost=localhost,
            lan=lan,
            public=None,
        )

    lan = [f"http://{ip}:{port}" for ip in get_local_ips()]
    public_ip = get_public_ip() if include_public else None
    public = f"http://{public_ip}:{port}" if public_ip else None
    return AccessUrls(
        bind_host=bind_host,
        port=port,
        localhost=localhost,
        lan=lan,
        public=public,
    )
