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
