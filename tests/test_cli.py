from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

from pylocalsend.cli import cli
from pylocalsend.core.utils import config as config_mod
from pylocalsend.core.utils import db as db_mod


@pytest.fixture(autouse=True)
def isolated_app_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    app_dir = tmp_path / "app"
    monkeypatch.setattr(config_mod, "APP_DIR", app_dir)
    monkeypatch.setattr(config_mod, "CONFIG_PATH", app_dir / "config.json")
    monkeypatch.setattr(config_mod, "SESSION_PATH", app_dir / "session.json")
    monkeypatch.setattr(db_mod, "APP_DIR", app_dir)
    return app_dir


@pytest.fixture
def output(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    stream = io.StringIO()
    console = Console(
        file=stream,
        force_terminal=False,
        color_system=None,
        width=1000,
    )
    monkeypatch.setattr(cli, "console", console)
    return stream


@pytest.fixture(autouse=True)
def no_logging_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "setup_logging", lambda: None)


@pytest.fixture(autouse=True)
def stable_network_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    from pylocalsend.core.transfer import sender as sender_mod
    from pylocalsend.core.utils import network as network_mod

    def fake_get_access_urls(
        port: int,
        bind_host: str = "0.0.0.0",
        *,
        include_public: bool = True,
    ) -> network_mod.AccessUrls:
        localhost = f"http://127.0.0.1:{port}"
        return network_mod.AccessUrls(
            bind_host=bind_host,
            port=port,
            localhost=localhost,
            lan=[],
            public=None,
        )

    monkeypatch.setattr(network_mod, "get_access_urls", fake_get_access_urls)
    monkeypatch.setattr(sender_mod, "get_access_urls", fake_get_access_urls)
    monkeypatch.setattr(cli, "get_access_urls", fake_get_access_urls)


def run_cli(args: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["pylocalsend", *args])
    cli.main()


def test_main_without_command_prints_help(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_cli([], monkeypatch)

    text = capsys.readouterr().out
    assert "LAN file transfer" in text
    assert "upload" in text
    assert "download" in text


def test_sender_generates_pin_and_stops_on_keyboard_interrupt(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {"stopped": False}

    def fake_start_server(cfg: config_mod.AppConfig, open_browser: bool) -> SimpleNamespace:
        from pylocalsend.core.utils import network as network_mod

        calls["pin"] = cfg.server_pin
        calls["open_browser"] = open_browser
        return SimpleNamespace(
            base_url="http://127.0.0.1:8765",
            access_urls=network_mod.AccessUrls(
                bind_host="0.0.0.0",
                port=8765,
                localhost="http://127.0.0.1:8765",
                lan=[],
                public=None,
            ),
        )

    def fake_sleep(_seconds: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "generate_pin", lambda: "123456")
    monkeypatch.setattr(cli, "start_server", fake_start_server)
    monkeypatch.setattr(cli, "stop_server", lambda: calls.update(stopped=True))
    monkeypatch.setattr(cli.time, "sleep", fake_sleep)

    run_cli(["sender", "--no-browser"], monkeypatch)

    text = output.getvalue()
    assert "Generated server PIN" in text
    assert "Sender running at http://127.0.0.1:8765" in text
    assert "Sender stopped." in text
    assert calls == {"stopped": True, "pin": "123456", "open_browser": False}
    assert config_mod.AppConfig.load().server_pin == "123456"


def test_upload_ls_rm_and_status_use_local_metadata(
    tmp_path: Path,
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = tmp_path / "shared.txt"
    shared.write_text("hello", encoding="utf-8")
    missing = tmp_path / "missing.txt"
    monkeypatch.setattr(cli, "_server_reachable", lambda: False)

    run_cli(["upload", str(shared), str(missing)], monkeypatch)
    run_cli(["ls"], monkeypatch)
    run_cli(["status"], monkeypatch)
    run_cli(["rm", str(shared), str(shared)], monkeypatch)

    text = output.getvalue()
    assert "Registered: shared.txt (5 bytes)" in text
    assert f"Failed {missing}:" in text
    assert "Shared files" in text
    assert "shared.txt" in text
    assert "http_server: stopped" in text
    assert "files_count: 1" in text
    assert "receivers_count: 0" in text
    assert f"Removed: {shared}" in text
    assert f"Not found: {shared}" in text


def test_config_show_and_set(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_cli(["config-set", "--key", "port", "9000"], monkeypatch)
    run_cli(["config-set", "--key", "pin_verification_enabled", "false"], monkeypatch)
    run_cli(["config-show", "--key", "port"], monkeypatch)
    run_cli(["config-show"], monkeypatch)

    text = output.getvalue()
    assert "Set port = 9000" in text
    assert "Set pin_verification_enabled = False" in text
    assert "port: 9000" in text
    assert "pin_verification_enabled: False" in text
    assert config_mod.AppConfig.load().port == 9000
    assert config_mod.AppConfig.load().pin_verification_enabled is False


def test_gen_pin_prints_generated_value(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "generate_pin", lambda: "654321")

    run_cli(["gen-pin"], monkeypatch)

    assert output.getvalue().strip() == "654321"


def test_receiver_new_ls_and_rm_by_id(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_cli(["receiver", "new", "--name", "laptop", "--pin", "111222"], monkeypatch)
    receiver = cli._local_service().db.list_receivers()[0]
    run_cli(["receiver", "ls"], monkeypatch)
    run_cli(["receiver", "rm", "--id", receiver["id"]], monkeypatch)
    run_cli(["receiver", "ls"], monkeypatch)

    text = output.getvalue()
    assert "Created receiver laptop" in text
    assert "PIN: 111222" in text
    assert "Link: http://127.0.0.1:8765/r/" in text
    assert "Receivers" in text
    assert "Receiver removed." in text
    assert cli._local_service().db.list_receivers() == []


def test_receiver_new_prompts_for_name_when_missing(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli.console, "input", lambda _prompt: "phone")
    monkeypatch.setattr(cli, "generate_pin", lambda: "222333")

    run_cli(["receiver", "new"], monkeypatch)

    text = output.getvalue()
    assert "Created receiver phone" in text
    assert "PIN: 222333" in text


def test_receiver_rm_handles_empty_list(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_cli(["receiver", "rm"], monkeypatch)

    assert "No receivers." in output.getvalue()


def test_receiver_rm_prompts_for_selection(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_cli(["receiver", "new", "--name", "tablet", "--pin", "333444"], monkeypatch)
    monkeypatch.setattr(cli.console, "input", lambda _prompt: "1")

    run_cli(["receiver", "rm"], monkeypatch)

    text = output.getvalue()
    assert "1. tablet" in text
    assert "Receiver removed." in text
    assert cli._local_service().db.list_receivers() == []


def test_receiver_command_without_subcommand_prints_usage(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_cli(["receiver"], monkeypatch)

    assert "Use: receiver new|rm|disable|enable|ls" in output.getvalue()


def test_receiver_disable_and_enable_by_id(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_server_reachable", lambda: False)
    run_cli(["receiver", "new", "--name", "laptop", "--pin", "111222"], monkeypatch)
    receiver = cli._local_service().db.list_receivers()[0]

    run_cli(["receiver", "disable", "--id", receiver["id"]], monkeypatch)
    run_cli(["receiver", "ls"], monkeypatch)
    run_cli(["receiver", "enable", "--id", receiver["id"]], monkeypatch)
    run_cli(["receiver", "ls"], monkeypatch)

    text = output.getvalue()
    assert "Receiver disabled." in text
    assert "已禁用" in text
    assert "Receiver enabled." in text
    assert "正常" in text
    assert cli._local_service().db.get_receiver(receiver["id"])["status"] == "active"


def test_grant_open_close_and_ls(
    tmp_path: Path,
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = tmp_path / "shared.txt"
    shared.write_text("hello", encoding="utf-8")
    folder = tmp_path / "photos"
    folder.mkdir()
    (folder / "a.jpg").write_bytes(b"a")
    (folder / "b.jpg").write_bytes(b"b")

    run_cli(["upload", str(shared), str(folder)], monkeypatch)
    run_cli(["grant", "close", str(shared)], monkeypatch)
    run_cli(["grant", "ls"], monkeypatch)
    run_cli(["grant", "open", str(shared)], monkeypatch)
    run_cli(["grant", "open", str(folder), "a.jpg"], monkeypatch)
    run_cli(["grant", "ls", "photos"], monkeypatch)
    run_cli(["grant", "close-all"], monkeypatch)
    run_cli(["grant", "open-all"], monkeypatch)

    text = output.getvalue()
    svc = cli._local_service()
    assert "Closed for download: shared.txt" in text
    assert "Download grants" in text
    assert "Opened for download: shared.txt" in text
    assert "Opened 1 path(s) under photos" in text
    assert "photos (dir) — partial (1)" in text
    assert "Closed 2 shared item(s) for download." in text
    assert "Opened 2 shared item(s) for download." in text
    assert svc.get_download_grants(svc.db.get_file_by_path(str(shared.resolve()))["id"]) == {""}


def test_ls_shows_open_column(
    tmp_path: Path,
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = tmp_path / "note.txt"
    shared.write_text("x", encoding="utf-8")
    run_cli(["upload", str(shared)], monkeypatch)
    run_cli(["grant", "close", str(shared)], monkeypatch)
    run_cli(["ls"], monkeypatch)

    text = output.getvalue()
    assert "Open" in text
    assert "closed" in text


def test_grant_command_without_subcommand_prints_usage(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_cli(["grant"], monkeypatch)

    assert "Use: grant ls|open|close|open-all|close-all" in output.getvalue()


def test_ls_remote_with_token_uses_receiver_view(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    class FakeReceiverClient:
        def __init__(self, host: str, pin: str, token: str | None = None) -> None:
            calls["host"] = host
            calls["pin"] = pin
            calls["token"] = token

        async def list_files(self) -> list[dict[str, object]]:
            return [{"name": "visible.txt", "is_dir": False, "size_human": "1 B"}]

    monkeypatch.setattr(cli, "ReceiverClient", FakeReceiverClient)

    run_cli(
        [
            "ls-remote",
            "-H",
            "http://sender/",
            "--pin",
            "123456",
            "--token",
            "abc-token",
        ],
        monkeypatch,
    )

    assert calls == {
        "host": "http://sender",
        "pin": "123456",
        "token": "abc-token",
    }
    text = output.getvalue()
    assert "(receiver view)" in text
    assert "visible.txt" in text


def test_connect_saves_trimmed_session(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_cli(["connect", "-H", "http://sender:8765/", "--pin", "123456"], monkeypatch)

    assert "Connected to http://sender:8765" in output.getvalue()
    assert config_mod.load_session() == {"host": "http://sender:8765", "pin": "123456"}


def test_resolve_connection_uses_explicit_args_before_session() -> None:
    config_mod.save_session("http://saved", "111111")
    args = SimpleNamespace(host="http://explicit/", pin="222222")

    assert cli._resolve_connection(args) == ("http://explicit", "222222")


def test_resolve_connection_uses_saved_session() -> None:
    config_mod.save_session("http://saved/", "111111")
    args = SimpleNamespace(host=None, pin=None)

    assert cli._resolve_connection(args) == ("http://saved", "111111")


def test_resolve_connection_exits_without_host_pin_or_session(
    output: io.StringIO,
) -> None:
    args = SimpleNamespace(host=None, pin=None)

    with pytest.raises(SystemExit) as excinfo:
        cli._resolve_connection(args)

    assert excinfo.value.code == 1
    assert "Not connected. Use connect or pass --host and --pin" in output.getvalue()


def test_ls_remote_lists_files(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeReceiverClient:
        def __init__(self, host: str, pin: str, token: str | None = None) -> None:
            self.host = host
            self.pin = pin
            self.token = token

        async def list_files(self) -> list[dict[str, object]]:
            return [
                {"name": "docs", "is_dir": True, "size_human": "2 KB"},
                {"name": "file.txt", "is_dir": False, "size_human": "5 B"},
            ]

    monkeypatch.setattr(cli, "ReceiverClient", FakeReceiverClient)

    run_cli(["ls-remote", "-H", "http://sender/", "--pin", "123456"], monkeypatch)

    text = output.getvalue()
    assert "Remote files @" in text
    assert "http://sender" in text
    assert "docs" in text
    assert "dir" in text
    assert "file.txt" in text


def test_download_uses_resolved_connection_and_configured_parallelism(
    tmp_path: Path,
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_mod.AppConfig.load().set("max_parallel", "7")
    calls: dict[str, object] = {}

    class FakeReceiverClient:
        def __init__(
            self,
            host: str,
            pin: str,
            token: str | None = None,
            max_parallel: int = 4,
        ) -> None:
            calls["host"] = host
            calls["pin"] = pin
            calls["token"] = token
            calls["max_parallel"] = max_parallel

        async def download_items(
            self,
            items: list[str],
            dest: Path,
            progress_callback,
        ) -> list[Path]:
            calls["items"] = items
            calls["dest"] = dest
            progress_callback("file.txt", 0, 5)
            progress_callback("file.txt", 5, 5)
            return [dest / "file.txt"]

    monkeypatch.setattr(cli, "ReceiverClient", FakeReceiverClient)

    run_cli(
        [
            "download",
            "file.txt",
            "-d",
            str(tmp_path / "downloads"),
            "-H",
            "http://sender/",
            "--pin",
            "123456",
        ],
        monkeypatch,
    )

    assert calls == {
        "host": "http://sender",
        "pin": "123456",
        "token": None,
        "max_parallel": 7,
        "items": ["file.txt"],
        "dest": (tmp_path / "downloads").resolve(),
    }
    assert "Downloaded 1 file(s) to" in output.getvalue()


def test_close_stops_in_process_server(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, bool] = {"stopped": False}
    monkeypatch.setattr(cli, "is_running", lambda: True)
    monkeypatch.setattr(cli, "stop_server", lambda: calls.update(stopped=True))

    run_cli(["close"], monkeypatch)

    assert calls == {"stopped": True}
    assert output.getvalue() == ""


def test_close_reports_when_sender_is_not_running(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "is_running", lambda: False)
    monkeypatch.setattr(cli, "_server_reachable", lambda: False)

    run_cli(["close"], monkeypatch)

    assert "Sender was not running." in output.getvalue()


def test_close_sends_shutdown_to_reachable_server(
    output: io.StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_mod.AppConfig.load().set("server_pin", "999000")
    calls: dict[str, object] = {}

    class FakeHttpx:
        @staticmethod
        def post(url: str, headers: dict[str, str], timeout: int) -> None:
            calls["url"] = url
            calls["headers"] = headers
            calls["timeout"] = timeout

    monkeypatch.setattr(cli, "is_running", lambda: False)
    monkeypatch.setattr(cli, "_server_reachable", lambda: True)
    monkeypatch.setitem(sys.modules, "httpx", FakeHttpx)

    run_cli(["close"], monkeypatch)

    assert calls == {
        "url": "http://127.0.0.1:8765/api/shutdown",
        "headers": {"X-PIN": "999000"},
        "timeout": 3,
    }
    assert "Sender closed." in output.getvalue()
