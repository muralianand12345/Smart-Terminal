"""
Terminal color and formatting utilities.

This module provides ANSI color codes and helper classes for consistent
terminal output styling throughout the application.
"""

import os
import sys
from typing import Any
from abc import ABC, abstractmethod


class ColorDisabled(Exception):
    """Exception raised when color output is not supported."""

    pass


class Colors:
    """
    Terminal color and formatting codes.

    This class provides ANSI color codes and helper methods for
    consistent terminal output styling throughout the application.
    """

    # Basic formatting
    RESET = "\033[0m"
    BOLD = "\033[1m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Text colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright text colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    # Bright background colors
    BG_BRIGHT_BLACK = "\033[100m"
    BG_BRIGHT_RED = "\033[101m"
    BG_BRIGHT_GREEN = "\033[102m"
    BG_BRIGHT_YELLOW = "\033[103m"
    BG_BRIGHT_BLUE = "\033[104m"
    BG_BRIGHT_MAGENTA = "\033[105m"
    BG_BRIGHT_CYAN = "\033[106m"
    BG_BRIGHT_WHITE = "\033[107m"

    # Flag to check if colors are supported
    _ENABLED = (
        sys.stdout.isatty()
        and os.environ.get("TERM") != "dumb"
        and not os.environ.get("NO_COLOR")
    )

    @classmethod
    def disable(cls) -> None:
        """Disable color output."""
        cls._ENABLED = False

    @classmethod
    def enable(cls) -> None:
        """Enable color output if terminal supports it."""
        cls._ENABLED = (
            sys.stdout.isatty()
            and os.environ.get("TERM") != "dumb"
            and not os.environ.get("NO_COLOR")
        )

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if color output is enabled."""
        return cls._ENABLED

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """
        Apply color to text.

        Args:
            text: Text to color
            color: Color code to apply

        Returns:
            Colored text if colors are enabled, otherwise original text
        """
        if not cls._ENABLED:
            return text
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def error(cls, text: str) -> str:
        """Format text as an error message (bright red)."""
        return cls.colorize(text, cls.BRIGHT_RED)

    @classmethod
    def success(cls, text: str) -> str:
        """Format text as a success message (bright green)."""
        return cls.colorize(text, cls.BRIGHT_GREEN)

    @classmethod
    def warning(cls, text: str) -> str:
        """Format text as a warning message (bright yellow)."""
        return cls.colorize(text, cls.BRIGHT_YELLOW)

    @classmethod
    def info(cls, text: str) -> str:
        """Format text as an informational message (bright blue)."""
        return cls.colorize(text, cls.BRIGHT_BLUE)

    @classmethod
    def cmd(cls, text: str) -> str:
        """Format text as a command (cyan)."""
        return cls.colorize(text, cls.CYAN)

    @classmethod
    def highlight(cls, text: str) -> str:
        """Format text as highlighted/important (bold white)."""
        return cls.colorize(text, f"{cls.BOLD}{cls.BRIGHT_WHITE}")

    @classmethod
    def dim(cls, text: str) -> str:
        """Format text as dimmed/less important."""
        return cls.colorize(text, cls.BRIGHT_BLACK)


class ColoredOutputProvider(ABC):
    """
    Abstract interface for colored output providers.

    This interface defines the methods that must be implemented
    by any class that provides colored output functionality.
    """

    @abstractmethod
    def error(self, text: str) -> None:
        """Print an error message."""
        pass

    @abstractmethod
    def success(self, text: str) -> None:
        """Print a success message."""
        pass

    @abstractmethod
    def warning(self, text: str) -> None:
        """Print a warning message."""
        pass

    @abstractmethod
    def info(self, text: str) -> None:
        """Print an informational message."""
        pass

    @abstractmethod
    def cmd(self, text: str) -> None:
        """Print a command."""
        pass

    @abstractmethod
    def highlight(self, text: str) -> None:
        """Print highlighted/important text."""
        pass


class ColoredOutput(ColoredOutputProvider):
    """
    Provides methods for printing colored output to the terminal.

    This class implements the ColoredOutputProvider interface and
    provides methods for printing different types of messages with
    consistent styling.
    """

    def error(self, text: str) -> None:
        """Print an error message."""
        print(Colors.error(text))

    def success(self, text: str) -> None:
        """Print a success message."""
        print(Colors.success(text))

    def warning(self, text: str) -> None:
        """Print a warning message."""
        print(Colors.warning(text))

    def info(self, text: str) -> None:
        """Print an informational message."""
        print(Colors.info(text))

    def cmd(self, text: str) -> None:
        """Print a command."""
        print(Colors.cmd(text))

    def highlight(self, text: str) -> None:
        """Print highlighted/important text."""
        print(Colors.highlight(text))

    def dim(self, text: str) -> None:
        """Print dimmed/less important text."""
        print(Colors.dim(text))

    def print(self, text: str, **kwargs: Any) -> None:
        """Print plain text with optional keyword arguments passed to print()."""
        print(text, **kwargs)


# Global instance for easier access
output = ColoredOutput()
