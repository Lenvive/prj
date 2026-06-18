from __future__ import annotations

import pytest

from pylocalsend.core.utils import network as network_mod


@pytest.fixture(autouse=True)
def reset_public_ip_cache() -> None:
    network_mod._PUBLIC_IP = network_mod._PUBLIC_IP_UNSET
    yield
    network_mod._PUBLIC_IP = network_mod._PUBLIC_IP_UNSET


def test_connect_host_maps_all_interfaces_to_loopback() -> None:
    assert network_mod.connect_host("0.0.0.0") == "127.0.0.1"
    assert network_mod.connect_host("") == "127.0.0.1"
    assert network_mod.connect_host("192.168.1.10") == "192.168.1.10"


def test_get_local_ips_uses_ifconfig_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable_socket(*_args: object, **_kwargs: object) -> None:
        raise OSError

    def unavailable_hostname(*_args: object, **_kwargs: object) -> None:
        raise OSError

    def fake_check_output(command: list[str], **_kwargs: object) -> str:
        assert command == ["ifconfig"]
        return """\
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
    inet 127.0.0.1 netmask 0xff000000
en0: flags=8863<UP,BROADCAST,SMART,RUNNING> mtu 1500
    inet 192.168.1.20 netmask 0xffffff00 broadcast 192.168.1.255
utun4: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1380
    inet 10.20.9.240 --> 10.20.9.240 netmask 0xffffffff
"""

    monkeypatch.setattr(network_mod.sys, "platform", "darwin")
    monkeypatch.setattr(network_mod.socket, "socket", unavailable_socket)
    monkeypatch.setattr(network_mod.socket, "getaddrinfo", unavailable_hostname)
    monkeypatch.setattr(network_mod.subprocess, "check_output", fake_check_output)

    assert network_mod.get_local_ips() == ["192.168.1.20", "10.20.9.240"]


def test_get_access_urls_for_all_interfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(network_mod, "get_local_ips", lambda: ["192.168.1.10", "10.0.0.5"])
    monkeypatch.setattr(network_mod, "get_public_ip", lambda **_: "203.0.113.8")

    urls = network_mod.get_access_urls(8765, "0.0.0.0")

    assert urls.primary == "http://192.168.1.10:8765"
    assert urls.localhost == "http://127.0.0.1:8765"
    assert urls.lan == [
        "http://192.168.1.10:8765",
        "http://10.0.0.5:8765",
    ]
    assert urls.public == "http://203.0.113.8:8765"
    assert urls.labels() == [
        ("本机", "http://127.0.0.1:8765"),
        ("局域网", "http://192.168.1.10:8765"),
        ("局域网 2", "http://10.0.0.5:8765"),
        ("公网", "http://203.0.113.8:8765"),
    ]


def test_get_access_urls_for_specific_host() -> None:
    urls = network_mod.get_access_urls(9000, "192.168.1.20")

    assert urls.primary == "http://192.168.1.20:9000"
    assert urls.lan == ["http://192.168.1.20:9000"]
    assert urls.public is None
