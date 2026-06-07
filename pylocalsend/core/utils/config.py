"""Application configuration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, get_type_hints

APP_DIR = Path.home() / ".pylocalsend"
CONFIG_PATH = APP_DIR / "config.json"
SESSION_PATH = APP_DIR / "session.json"

CONFIG_KEYS = {
    "host": "host",
    "port": "port",
    "chunk_size": "chunk_size",
    "max_parallel": "max_parallel",
    "encryption_enabled": "encryption_enabled",
    "pin_verification_enabled": "pin_verification_enabled",
    "server_pin": "server_pin",
}


@dataclass
class AppConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    chunk_size: int = 8 * 1024 * 1024
    max_parallel: int = 4
    encryption_enabled: bool = True
    pin_verification_enabled: bool = True
    server_pin: str = ""

    @classmethod
    def load(cls) -> AppConfig:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if not CONFIG_PATH.exists():
            cfg = cls()
            cfg.save()
            return cfg
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str) -> Any:
        if key not in CONFIG_KEYS and key not in {f.name for f in fields(self)}:
            raise KeyError(f"Unknown config key: {key}")
        return getattr(self, key)

    def set(self, key: str, value: Any) -> None:
        if not hasattr(self, key):
            raise KeyError(f"Unknown config key: {key}")
        field_map = get_type_hints(type(self))
        expected = field_map[key]
        if expected is bool:
            if isinstance(value, str):
                value = value.lower() in ("1", "true", "yes", "on")
            else:
                value = bool(value)
        elif expected is int:
            value = int(value)
        elif expected is str:
            value = str(value)
        setattr(self, key, value)
        self.save()

    def as_display_dict(self) -> dict[str, Any]:
        return asdict(self)


def save_session(host: str, pin: str) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(
        json.dumps({"host": host.rstrip("/"), "pin": pin}, indent=2),
        encoding="utf-8",
    )


def load_session() -> dict[str, str] | None:
    if not SESSION_PATH.exists():
        return None
    return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
