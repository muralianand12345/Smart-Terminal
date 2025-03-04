"""
Command Line Interface for SmartTerminal.

This package provides the command-line interface, argument parsing,
and the main entry point for the application.
"""

from smart_terminal.cli.main import main, run_cli
from smart_terminal.cli.arguments import parse_arguments
from smart_terminal.cli.interactive import run_interactive_mode

__all__ = ["main", "run_cli", "parse_arguments", "run_interactive_mode"]
