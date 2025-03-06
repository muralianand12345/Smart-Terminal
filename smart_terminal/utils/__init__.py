"""
Utility functions and classes for SmartTerminal.

This module provides utility functions and helper classes used throughout
the application, including terminal colors, logging setup, and common
helper functions.
"""

from smart_terminal.utils.colors import Colors, ColoredOutput
from smart_terminal.utils.logging import setup_logging, get_logger
from smart_terminal.utils.helpers import (
    print_error,
    print_warning,
    print_success,
    print_info,
    print_banner,
    safe_execute,
    deprecated,
)

__all__ = [
    # Terminal coloring utilities
    "Colors",
    "ColoredOutput",
    # Logging utilities
    "setup_logging",
    "get_logger",
    # Helper functions
    "print_error",
    "print_warning",
    "print_success",
    "print_info",
    "print_banner",
    "safe_execute",
    "deprecated",
]
