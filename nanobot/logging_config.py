"""Centralized Loguru configuration for nanobot."""

from pathlib import Path
import sys

from loguru import logger

from nanobot.utils.helpers import ensure_dir

_FILE_SINK_ID: int | None = None
_CONSOLE_SINK_ID: int | None = None


def get_log_file_path() -> Path:
    """Return the single nanobot log file path, creating its directory if needed."""
    logs_dir = ensure_dir(Path.home() / ".nanobot" / "logs")
    return logs_dir / "nanobot.log"


def configure_logging(console: bool = True) -> Path:
    """Configure Loguru sinks once; always keep a single file sink enabled."""
    global _FILE_SINK_ID

    if _FILE_SINK_ID is None:
        logger.remove()
        _FILE_SINK_ID = logger.add(
            str(get_log_file_path()),
            level="DEBUG",
            enqueue=True,
            backtrace=False,
            diagnose=False,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
        )

    set_console_logging(console)
    return get_log_file_path()


def set_console_logging(enabled: bool) -> None:
    """Enable/disable stderr logging without affecting file logging."""
    global _CONSOLE_SINK_ID

    if enabled and _CONSOLE_SINK_ID is None:
        _CONSOLE_SINK_ID = logger.add(
            sys.stderr,
            level="INFO",
            colorize=True,
            format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )
    elif not enabled and _CONSOLE_SINK_ID is not None:
        logger.remove(_CONSOLE_SINK_ID)
        _CONSOLE_SINK_ID = None
