"""
Custom exceptions for SmartTerminal.

This package provides a hierarchy of custom exceptions used throughout the application
to handle various error scenarios in a consistent way.
"""

from smart_terminal.exceptions.errors import (
    SmartTerminalError,
    ConfigError,
    AIError,
    CommandError,
    ShellError,
    AdapterError,
    PermissionError,
    TimeoutError,
    ValidationError,
    NotFoundError,
)

__all__ = [
    "SmartTerminalError",
    "ConfigError",
    "AIError",
    "CommandError",
    "ShellError",
    "AdapterError",
    "PermissionError",
    "TimeoutError",
    "ValidationError",
    "NotFoundError",
]
