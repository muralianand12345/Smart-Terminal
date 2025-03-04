"""
Utility functions and classes for SmartTerminal.

This module provides utility functions and helper classes used throughout the application,
including terminal colors, logging setup, and common helper functions.
"""

import json
import logging
from typing import Dict, Any

# Setup top-level logger
logger = logging.getLogger("smartterminal")


class Colors:
    """
    Terminal color and formatting codes for improved user experience.

    This class provides ANSI color codes and helper methods for consistent
    terminal output styling throughout the application.
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    @classmethod
    def error(cls, text: str) -> str:
        """Format text as an error message."""
        return f"{cls.RED}{text}{cls.RESET}"

    @classmethod
    def success(cls, text: str) -> str:
        """Format text as a success message."""
        return f"{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def warning(cls, text: str) -> str:
        """Format text as a warning message."""
        return f"{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def info(cls, text: str) -> str:
        """Format text as an informational message."""
        return f"{cls.BLUE}{text}{cls.RESET}"

    @classmethod
    def cmd(cls, text: str) -> str:
        """Format text as a command."""
        return f"{cls.CYAN}{text}{cls.RESET}"

    @classmethod
    def highlight(cls, text: str) -> str:
        """Format text as highlighted/important."""
        return f"{cls.BOLD}{text}{cls.RESET}"


def setup_logging(level_name: str = "INFO") -> None:
    """
    Configure application-wide logging based on the specified level.

    Args:
        level_name (str): Logging level name (DEBUG, INFO, WARNING, ERROR)
    """
    level = getattr(logging, level_name.upper(), logging.INFO)

    # Clear existing handlers
    logger.handlers = []

    # Set level
    logger.setLevel(level)

    if level == logging.DEBUG:
        # Debug format with timestamp
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Debug OpenAI HTTP requests
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.INFO)
        httpx_logger.addHandler(handler)
    else:
        # Silent handler that doesn't output anything
        class NullHandler(logging.Handler):
            def emit(self, record):
                pass

        # Disable other loggers
        logging.getLogger("httpx").setLevel(logging.WARNING)

        # Add null handler to prevent "No handler found" warnings
        logger.addHandler(NullHandler())


def print_error(message: str) -> None:
    """
    Print an error message to the console.

    Args:
        message (str): The error message to print.
    """
    print(Colors.error(f"Error: {message}"))


def print_banner():
    """Print a fancy banner for the application."""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════╗
║                                                  ║
║  {Colors.GREEN}SmartTerminal{Colors.CYAN}                                  ║
║  {Colors.BLUE}AI-Powered Terminal Commands{Colors.CYAN}                    ║
║                                                  ║
╚══════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def parse_command_args(args_json: str) -> Dict[str, Any]:
    """
    Parse JSON arguments from AI tool call.

    Args:
        args_json (str): JSON string of arguments

    Returns:
        Dict[str, Any]: Parsed arguments as a dictionary

    Raises:
        ValueError: If JSON parsing fails
    """
    try:
        return dict(json.loads(args_json))
    except Exception as e:
        raise ValueError(f"Failed to parse command arguments: {e}")
