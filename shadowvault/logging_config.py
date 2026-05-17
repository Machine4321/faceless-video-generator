"""
shadowvault/logging_config.py
Logging configuration with rotating file handler + coloured console output.

Usage:
    from shadowvault.logging_config import setup_logging
    setup_logging()  # call once at startup
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ANSI colour codes for console output
_COLORS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[41m",  # red background
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    """Formatter that adds ANSI colours to the level name in terminal output."""

    def __init__(self, fmt: str, datefmt: str | None = None) -> None:
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname:<8}{_RESET}"
        return super().format(record)


def setup_logging(
    log_dir: str | None = None,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Configure the root logger with:
      - A RotatingFileHandler (10 MB, 5 backups) writing to log_dir/shadowvault.log
      - A console (stderr) handler with ANSI colours

    Parameters
    ----------
    log_dir      : directory for log files; if None uses PROJECT_ROOT/logs
    level        : minimum log level
    max_bytes    : max size per log file before rotation
    backup_count : number of rotated log files to keep
    """
    if log_dir is None:
        from shadowvault.config import PROJECT_ROOT
        log_dir = str(PROJECT_ROOT / "logs")

    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "shadowvault.log")

    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to avoid duplicates on re-init
    root.handlers.clear()

    # File handler (plain text, no colours)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(file_handler)

    # Console handler (with ANSI colours)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(_ColorFormatter(fmt, datefmt))
    root.addHandler(console_handler)

    logging.getLogger("moviepy").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
