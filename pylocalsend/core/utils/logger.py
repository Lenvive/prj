"""Logging helpers."""

from __future__ import annotations

import logging
import sys

_LOG = logging.getLogger("pylocalsend")


def setup_logging(level: int = logging.INFO) -> None:
    if _LOG.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    _LOG.addHandler(handler)
    _LOG.setLevel(level)


def get_logger(name: str | None = None) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name or "pylocalsend")
