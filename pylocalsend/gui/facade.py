"""Facade exposing core sender operations to GUI."""

from __future__ import annotations

from typing import Any

from pylocalsend.core.transfer.server_entry import get_service, is_running, start_server
from pylocalsend.core.utils.config import AppConfig


class SenderFacade:
    def ensure_running(self) -> None:
        if not is_running():
            cfg = AppConfig.load()
            if not cfg.server_pin and cfg.pin_verification_enabled:
                from pylocalsend.core.utils.crypto import generate_pin
                cfg.server_pin = generate_pin()
                cfg.save()
            start_server(cfg)

    @property
    def service(self):
        self.ensure_running()
        return get_service()

    def list_files(self) -> list[dict[str, Any]]:
        return self.service.list_files_local()

    def register_paths(self, paths: list[str]) -> list[dict[str, Any]]:
        return [self.service.register_path(p) for p in paths]

    def remove_file(self, file_id: str) -> None:
        self.service.db.remove_file_by_id(file_id)

    def folder_contents(self, file_id: str) -> list[dict[str, Any]]:
        from pathlib import Path
        from pylocalsend.core.file_handler.file_handler import list_dir_contents

        record = self.service.db.get_file(file_id)
        if not record:
            return []
        return list_dir_contents(Path(record["path"]))

    def folder_path_contents(self, path: str) -> list[dict[str, Any]]:
        from pathlib import Path
        from pylocalsend.core.file_handler.file_handler import list_dir_contents

        return list_dir_contents(Path(path))

    def file_downloads(self, file_id: str) -> list[dict[str, Any]]:
        return self.service.db.list_downloads_for_file(file_id)

    def list_receivers(self) -> list[dict[str, Any]]:
        from pylocalsend.core.transfer.sender import _receiver_to_api
        return [
            _receiver_to_api(r, self.service.base_url)
            for r in self.service.db.list_receivers()
        ]

    def create_receiver(self, name: str, pin: str | None = None) -> dict[str, Any]:
        return self.service.create_receiver(name, pin)

    def remove_receiver(self, receiver_id: str) -> None:
        self.service.db.remove_receiver(receiver_id)

    def disable_receiver(self, receiver_id: str) -> None:
        self.service.disable_receiver(receiver_id)

    def enable_receiver(self, receiver_id: str) -> None:
        self.service.enable_receiver(receiver_id)

    def receiver_downloads(self, receiver_id: str) -> list[dict[str, Any]]:
        return self.service.db.list_downloads_for_receiver(receiver_id)

    def get_config(self) -> dict[str, Any]:
        return self.service.config.as_display_dict()

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        for k, v in updates.items():
            if hasattr(self.service.config, k):
                self.service.config.set(k, v)
        return self.get_config()

    @property
    def base_url(self) -> str:
        return self.service.base_url

    @property
    def access_urls(self):
        return self.service.access_urls
