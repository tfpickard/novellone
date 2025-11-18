from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterable

from rich.console import Console
from rich.logging import RichHandler
from rich.pretty import pretty_repr

from config import AppSettings

_configured = False


class PrettyJsonFormatter(logging.Formatter):
    """Formatter that pretty-prints JSON objects in log messages."""

    def format(self, record: logging.LogRecord) -> str:
        # Format the message first with the original args
        msg = super().format(record)
        # No modifications needed - just return formatted message
        # Rich pretty-printing happens in console handler via RichHandler
        return msg


def _build_handlers(settings: AppSettings, level: int) -> Iterable[logging.Handler]:
    # Use Rich handler for console with pretty printing
    # Set a wider console width to prevent excessive wrapping in Docker logs
    # Disable Rich markup globally to avoid user-provided text (e.g. "[/CHANT]")
    # from being treated as Rich markup tags, which can raise MarkupError and
    # break logging output.
    console_handler = RichHandler(
        console=Console(stderr=True, width=120, force_terminal=True),
        show_time=True,
        show_path=True,
        markup=False,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )
    console_handler.setLevel(level)

    # Use pretty JSON formatter for file logs
    file_formatter = PrettyJsonFormatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "backend.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)

    return console_handler, file_handler


def configure_logging(settings: AppSettings) -> None:
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handlers = list(_build_handlers(settings, level))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers.clear()
        for handler in handlers:
            logger.addHandler(handler)
        logger.propagate = False

    _configured = True


__all__ = ["configure_logging"]
