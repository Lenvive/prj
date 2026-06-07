"""Command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TaskID, TextColumn, TransferSpeedColumn
from rich.table import Table

from pylocalsend.core.receiver.receiver import ReceiverClient
from pylocalsend.core.transfer.sender import SenderService
from pylocalsend.core.transfer.server_entry import (
    get_service,
    is_running,
    start_server,
    stop_server,
)
from pylocalsend.core.utils.config import (
    AppConfig,
    load_session,
    save_session,
)
from pylocalsend.core.utils.crypto import generate_pin
from pylocalsend.core.utils.logger import setup_logging
from pylocalsend.core.utils.network import connect_host, get_access_urls

console = Console()


def _local_service() -> SenderService:
    """Local metadata operations — no HTTP server required."""
    return SenderService(AppConfig.load())


def _server_reachable() -> bool:
    cfg = AppConfig.load()
    return _port_in_use(connect_host(cfg.host), cfg.port)


def _print_access_urls(port: int, bind_host: str) -> None:
    urls = get_access_urls(port, bind_host)
    console.print(f"base_url: [bold]{urls.primary}[/bold]")
    for label, url in urls.labels():
        console.print(f"  {label}: {url}")
    if urls.public:
        console.print("  [dim]公网地址需路由器端口映射后才可从外网访问[/dim]")


def _port_in_use(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def cmd_gui(_args: argparse.Namespace) -> None:
    from pylocalsend.gui.sender.app import run_sender_gui

    run_sender_gui()


def cmd_sender(args: argparse.Namespace) -> None:
    cfg = AppConfig.load()
    if not cfg.server_pin and cfg.pin_verification_enabled:
        cfg.server_pin = generate_pin()
        cfg.save()
        console.print(f"[green]Generated server PIN:[/green] {cfg.server_pin}")
    svc = start_server(cfg, open_browser=args.open_browser)
    console.print(f"Sender running at [bold]{svc.base_url}[/bold]")
    for label, url in svc.access_urls.labels():
        if url != svc.base_url:
            console.print(f"  {label}: {url}")
    if svc.access_urls.public:
        console.print("  [dim]公网地址需路由器端口映射后才可从外网访问[/dim]")
    console.print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_server()
        console.print("Sender stopped.")


def cmd_upload(args: argparse.Namespace) -> None:
    svc = _local_service()
    for path in args.paths:
        try:
            record = svc.register_path(path)
            console.print(f"Registered: {record['name']} ({record['size']} bytes)")
        except Exception as e:
            console.print(f"[red]Failed {path}:[/red] {e}")


def cmd_rm(args: argparse.Namespace) -> None:
    svc = _local_service()
    for path in args.paths:
        if svc.remove_path(path):
            console.print(f"Removed: {path}")
        else:
            console.print(f"[yellow]Not found:[/yellow] {path}")


def cmd_ls(_args: argparse.Namespace) -> None:
    files = _local_service().list_files_local()
    table = Table(title="Shared files")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Size")
    table.add_column("Status")
    table.add_column("Uploaded")
    for f in files:
        table.add_row(
            f["name"],
            "dir" if f["is_dir"] else "file",
            f["size_human"],
            f["status"],
            f["uploaded_at"],
        )
    console.print(table)


def cmd_config_show(args: argparse.Namespace) -> None:
    cfg = AppConfig.load()
    data = cfg.as_display_dict()
    if args.key:
        console.print(f"{args.key}: {cfg.get(args.key)}")
    else:
        for k, v in data.items():
            console.print(f"{k}: {v}")


def cmd_config_set(args: argparse.Namespace) -> None:
    cfg = AppConfig.load()
    cfg.set(args.key, args.value)
    console.print(f"Set {args.key} = {cfg.get(args.key)}")


def cmd_gen_pin(_args: argparse.Namespace) -> None:
    pin = generate_pin()
    console.print(pin)


def cmd_receiver_new(args: argparse.Namespace) -> None:
    svc = _local_service()
    name = args.name or console.input("Receiver name: ")
    pin = args.pin or generate_pin()
    rec = svc.create_receiver(name, pin)
    console.print(f"Created receiver [bold]{rec['name']}[/bold]")
    console.print(f"PIN: {rec['pin']}")
    console.print(f"Link: {rec['link']}")


def cmd_receiver_rm(args: argparse.Namespace) -> None:
    svc = _local_service()
    receivers = svc.db.list_receivers()
    if not receivers:
        console.print("No receivers.")
        return
    if args.id:
        rid = args.id
    else:
        for i, r in enumerate(receivers):
            console.print(f"{i + 1}. {r['name']} ({r['id'][:8]}...)")
        choice = int(console.input("Select number: ")) - 1
        rid = receivers[choice]["id"]
    if svc.db.remove_receiver(rid):
        console.print("Receiver removed.")
    else:
        console.print("[red]Not found[/red]")


def cmd_receiver_ls(_args: argparse.Namespace) -> None:
    svc = _local_service()
    receivers = svc.db.list_receivers()
    table = Table(title="Receivers")
    table.add_column("Name")
    table.add_column("Link")
    table.add_column("Status")
    table.add_column("PIN")
    from pylocalsend.core.transfer.sender import _receiver_to_api

    for r in receivers:
        info = _receiver_to_api(r, svc.base_url)
        table.add_row(info["name"], info["link"], info["status"], info["pin"])
    console.print(table)


def cmd_status(_args: argparse.Namespace) -> None:
    cfg = AppConfig.load()
    svc = _local_service()
    online = _server_reachable()
    console.print(f"http_server: {'running' if online else 'stopped'}")
    _print_access_urls(cfg.port, cfg.host)
    console.print(f"files_count: {len(svc.db.list_files())}")
    console.print(f"receivers_count: {len(svc.db.list_receivers())}")
    if online:
        try:
            import httpx

            pin = cfg.server_pin if cfg.pin_verification_enabled else ""
            r = httpx.get(
                f"http://{connect_host(cfg.host)}:{cfg.port}/api/status",
                headers={"X-PIN": pin},
                timeout=3,
            )
            if r.status_code == 200:
                for k, v in r.json().items():
                    console.print(f"{k}: {v}")
        except Exception as e:
            console.print(f"[yellow]Could not query live status: {e}[/yellow]")


def cmd_close(_args: argparse.Namespace) -> None:
    if is_running():
        stop_server()
    elif _server_reachable():
        import httpx

        cfg = AppConfig.load()
        try:
            httpx.post(
                f"http://{connect_host(cfg.host)}:{cfg.port}/api/shutdown",
                headers={"X-PIN": cfg.server_pin},
                timeout=3,
            )
        except Exception:
            pass
        console.print("Sender closed.")
    else:
        console.print("Sender was not running.")


def cmd_ls_remote(args: argparse.Namespace) -> None:
    host, pin = _resolve_connection(args)
    files = asyncio.run(ReceiverClient(host, pin).list_files())
    table = Table(title=f"Remote files @ {host}")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Size")
    for f in files:
        table.add_row(f["name"], "dir" if f["is_dir"] else "file", f["size_human"])
    console.print(table)


def cmd_connect(args: argparse.Namespace) -> None:
    host = args.host.rstrip("/")
    pin = args.pin
    save_session(host, pin)
    console.print(f"Connected to {host}")


def cmd_download(args: argparse.Namespace) -> None:
    host, pin = _resolve_connection(args)
    dest = Path(args.dest or ".").resolve()
    cfg = AppConfig.load()
    client = ReceiverClient(host, pin, max_parallel=cfg.max_parallel)

    progress = Progress(
        TextColumn("[bold blue]{task.fields[label]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        console=console,
    )
    tasks: dict[str, TaskID] = {}

    def on_progress(label: str, done: int, total: int) -> None:
        if label not in tasks:
            tasks[label] = progress.add_task("", total=total, label=label)
        progress.update(tasks[label], completed=done, total=total)

    with progress:
        paths = asyncio.run(
            client.download_items(args.items, dest, progress_callback=on_progress)
        )
    console.print(f"Downloaded {len(paths)} file(s) to {dest}")


def _resolve_connection(args: argparse.Namespace) -> tuple[str, str]:
    host = getattr(args, "host", None)
    pin = getattr(args, "pin", None)
    if host and pin:
        return host.rstrip("/"), pin
    session = load_session()
    if session:
        return session["host"], session["pin"]
    console.print("[red]Not connected. Use connect or pass --host and --pin[/red]")
    sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pylocalsend", description="LAN file transfer")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("gui", help="Start sender WebUI")
    sp = sub.add_parser("sender", help="Start sender service")
    sp.add_argument("--no-browser", action="store_true")

    sp = sub.add_parser("upload", help="Register files/dirs for sharing")
    sp.add_argument("paths", nargs="+")

    sp = sub.add_parser("rm", help="Remove shared paths")
    sp.add_argument("paths", nargs="+")

    sub.add_parser("ls", help="List shared files")
    sub.add_parser("status", help="Sender status")
    sub.add_parser("close", help="Stop sender")
    sub.add_parser("gen-pin", help="Generate PIN")

    sp = sub.add_parser("config-show")
    sp.add_argument("--key", dest="key", default=None)

    sp = sub.add_parser("config-set")
    sp.add_argument("--key", dest="key", required=True)
    sp.add_argument("value")

    recv = sub.add_parser("receiver")
    recv_sub = recv.add_subparsers(dest="receiver_cmd")
    sp = recv_sub.add_parser("new")
    sp.add_argument("--name", default=None)
    sp.add_argument("--pin", default=None)
    sp = recv_sub.add_parser("rm")
    sp.add_argument("--id", default=None)
    recv_sub.add_parser("ls")

    sp = sub.add_parser("ls-remote")
    sp.add_argument("-H", "--host", required=True)
    sp.add_argument("--pin", required=True)

    sp = sub.add_parser("connect")
    sp.add_argument("-H", "--host", required=True)
    sp.add_argument("--pin", required=True)

    sp = sub.add_parser("download")
    sp.add_argument("items", nargs="+")
    sp.add_argument("-d", "--dest", default=".")
    sp.add_argument("-H", "--host", default=None)
    sp.add_argument("--pin", default=None)

    return p


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    handlers = {
        "gui": cmd_gui,
        "sender": cmd_sender,
        "upload": cmd_upload,
        "rm": cmd_rm,
        "ls": cmd_ls,
        "config-show": cmd_config_show,
        "config-set": cmd_config_set,
        "gen-pin": cmd_gen_pin,
        "status": cmd_status,
        "close": cmd_close,
        "ls-remote": cmd_ls_remote,
        "connect": cmd_connect,
        "download": cmd_download,
    }

    if args.command == "receiver":
        rc = {
            "new": cmd_receiver_new,
            "rm": cmd_receiver_rm,
            "ls": cmd_receiver_ls,
        }
        fn = rc.get(args.receiver_cmd)
        if fn:
            fn(args)
        else:
            console.print("Use: receiver new|rm|ls")
        return

    if args.command == "sender":
        args.open_browser = not getattr(args, "no_browser", False)
        cmd_sender(args)
        return

    handlers[args.command](args)


if __name__ == "__main__":
    main()
