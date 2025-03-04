"""
Logging utilities for SmartTerminal.

This module provides functions for setting up and using the application's
logging system in a consistent way across all components.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler


# Default log format strings
DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
VERBOSE_FORMAT = (
    "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(funcName)s - %(message)s"
)
SIMPLE_FORMAT = "%(levelname)s - %(message)s"

# Log directory
LOG_DIR = Path.home() / ".smartterminal" / "logs"


class NullHandler(logging.Handler):
    """Handler that does nothing, used for silent logging."""

    def emit(self, record: logging.LogRecord) -> None:
        """Do nothing with the log record."""
        pass


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name, typically __name__ or module path

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def setup_logging(
    level_name: str = "INFO",
    log_file: bool = False,
    log_to_console: bool = True,
    format_string: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 3,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level_name: Logging level name (DEBUG, INFO, WARNING, ERROR)
        log_file: Whether to log to a file
        log_to_console: Whether to log to the console
        format_string: Custom format string for log messages
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
    """
    # Get the numeric level from the name
    level = getattr(logging, level_name.upper(), logging.INFO)

    # Create log directory if logging to file
    if log_file:
        LOG_DIR.mkdir(exist_ok=True, parents=True)

    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set level
    root_logger.setLevel(level)

    # Choose format string based on level
    if format_string is None:
        if level == logging.DEBUG:
            format_string = VERBOSE_FORMAT
        else:
            format_string = DEFAULT_FORMAT

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Add console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Add file handler if requested
    if log_file:
        log_file_path = LOG_DIR / "smartterminal.log"
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=max_file_size, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure known third-party loggers
    if level != logging.DEBUG:
        # Silence httpx and other noisy libraries in non-debug mode
        for logger_name in ["httpx", "httpcore", "openai"]:
            third_party_logger = logging.getLogger(logger_name)
            third_party_logger.setLevel(logging.WARNING)
            third_party_logger.addHandler(NullHandler())

    # Log setup information
    logging.debug(f"Logging initialized with level {level_name}")
    if log_file:
        logging.debug(f"Logging to file: {log_file_path}")


def disable_all_logging() -> None:
    """
    Disable all logging output.

    This is useful for unit tests or when logging needs to be
    temporarily disabled.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.CRITICAL + 1)

    # Remove all handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add null handler
    root_logger.addHandler(NullHandler())


def enable_debug_logging() -> None:
    """
    Enable debug logging for everything.

    This is useful for debugging issues where you need to see
    all logging output.
    """
    setup_logging(level_name="DEBUG", log_file=True, format_string=VERBOSE_FORMAT)

    logging.debug("Debug logging enabled")


def check_log_file() -> Dict[str, Any]:
    """
    Check the status of the log file.

    Returns:
        Dictionary with log file information
    """
    log_file_path = LOG_DIR / "smartterminal.log"

    if not log_file_path.exists():
        return {
            "exists": False,
            "path": str(log_file_path),
            "size": 0,
            "is_writable": os.access(LOG_DIR, os.W_OK),
        }

    return {
        "exists": True,
        "path": str(log_file_path),
        "size": log_file_path.stat().st_size,
        "last_modified": log_file_path.stat().st_mtime,
        "is_writable": os.access(log_file_path, os.W_OK),
    }


def clear_logs() -> bool:
    """
    Clear all log files.

    Returns:
        True if logs were cleared successfully, False otherwise
    """
    try:
        log_file_path = LOG_DIR / "smartterminal.log"

        if log_file_path.exists():
            log_file_path.unlink()

        # Also clear backup log files
        for backup_file in LOG_DIR.glob("smartterminal.log.*"):
            backup_file.unlink()

        return True
    except Exception as e:
        logging.error(f"Failed to clear logs: {e}")
        return False
