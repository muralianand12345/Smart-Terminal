"""
Argument parsing for SmartTerminal CLI.

This module handles command-line argument parsing for the application,
defining available commands and options.
"""

import logging
import argparse
from typing import Optional, List
from argparse import Namespace

from smart_terminal import __version__

# Setup logging
logger = logging.getLogger(__name__)


def parse_arguments(args: Optional[List[str]] = None) -> Namespace:
    """
    Parse command-line arguments.

    Args:
        args: Optional list of arguments to parse (defaults to sys.argv)

    Returns:
        Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="SmartTerminal - Natural language to terminal commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  st "create a directory named projects and initialize a git repository in it"
  st -i  # Start interactive mode
  st --setup  # Configure SmartTerminal
        """,
    )

    # Single command argument
    parser.add_argument(
        "command", nargs="?", help="Natural language command to execute"
    )

    # Setup and configuration
    setup_group = parser.add_argument_group("Setup and Configuration")
    setup_group.add_argument(
        "--setup", action="store_true", help="Set up SmartTerminal configuration"
    )
    setup_group.add_argument(
        "--clear-history", action="store_true", help="Clear command history"
    )
    setup_group.add_argument(
        "--shell-setup", action="store_true", help="Set up shell integration"
    )

    # Mode options
    mode_group = parser.add_argument_group("Mode Options")
    mode_group.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    mode_group.add_argument(
        "--dry-run", action="store_true", help="Show commands without executing them"
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    output_group.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress non-essential output"
    )
    output_group.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    # Information options
    info_group = parser.add_argument_group("Information")
    info_group.add_argument(
        "--version", "-v", action="store_true", help="Show version information"
    )
    info_group.add_argument(
        "--config-info", action="store_true", help="Show configuration information"
    )

    # Advanced options
    advanced_group = parser.add_argument_group("Advanced Options")
    advanced_group.add_argument("--api-key", help="Set API key for this session only")
    advanced_group.add_argument("--model", help="Set AI model for this session only")
    advanced_group.add_argument(
        "--base-url", help="Set API base URL for this session only"
    )
    advanced_group.add_argument(
        "--os",
        choices=["macos", "linux", "windows"],
        help="Target operating system for commands",
    )

    parsed_args = parser.parse_args(args)
    logger.debug(f"Parsed arguments: {parsed_args}")

    return parsed_args


def validate_args(args: Namespace) -> bool:
    """
    Validate parsed command-line arguments.

    Check for conflicts, invalid combinations, or missing required arguments.

    Args:
        args: Parsed arguments

    Returns:
        bool: True if arguments are valid, False otherwise
    """
    # Check for conflicting options
    conflicts = [
        (args.setup and args.command, "--setup cannot be used with a command"),
        (
            args.clear_history and args.command,
            "--clear-history cannot be used with a command",
        ),
        (
            args.shell_setup and args.command,
            "--shell-setup cannot be used with a command",
        ),
        (args.setup and args.interactive, "--setup cannot be used with --interactive"),
        (
            args.dry_run and (args.setup or args.clear_history or args.shell_setup),
            "--dry-run cannot be used with setup commands",
        ),
        (args.quiet and args.debug, "--quiet cannot be used with --debug"),
    ]

    for conflict_condition, conflict_message in conflicts:
        if conflict_condition:
            return False

    # Check for required arguments
    if not any(
        [
            args.command,
            args.interactive,
            args.setup,
            args.clear_history,
            args.shell_setup,
            args.version,
            args.config_info,
        ]
    ):
        return False

    return True


def get_help_text() -> str:
    """
    Get the full help text for the CLI.

    Returns:
        str: Full help text
    """
    parser = argparse.ArgumentParser(
        description="SmartTerminal - Natural language to terminal commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  st "create a directory named projects and initialize a git repository in it"
  st -i  # Start interactive mode
  st --setup  # Configure SmartTerminal
        """,
    )

    # Add the same arguments as in parse_arguments
    # Single command argument
    parser.add_argument(
        "command", nargs="?", help="Natural language command to execute"
    )

    # Setup and configuration
    setup_group = parser.add_argument_group("Setup and Configuration")
    setup_group.add_argument(
        "--setup", action="store_true", help="Set up SmartTerminal configuration"
    )
    setup_group.add_argument(
        "--clear-history", action="store_true", help="Clear command history"
    )
    setup_group.add_argument(
        "--shell-setup", action="store_true", help="Set up shell integration"
    )

    # Mode options
    mode_group = parser.add_argument_group("Mode Options")
    mode_group.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    mode_group.add_argument(
        "--dry-run", action="store_true", help="Show commands without executing them"
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    output_group.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress non-essential output"
    )
    output_group.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    # Information options
    info_group = parser.add_argument_group("Information")
    info_group.add_argument(
        "--version", "-v", action="store_true", help="Show version information"
    )
    info_group.add_argument(
        "--config-info", action="store_true", help="Show configuration information"
    )

    # Advanced options
    advanced_group = parser.add_argument_group("Advanced Options")
    advanced_group.add_argument("--api-key", help="Set API key for this session only")
    advanced_group.add_argument("--model", help="Set AI model for this session only")
    advanced_group.add_argument(
        "--base-url", help="Set API base URL for this session only"
    )
    advanced_group.add_argument(
        "--os",
        choices=["macos", "linux", "windows"],
        help="Target operating system for commands",
    )

    # Get the help text
    import io

    help_output = io.StringIO()
    parser.print_help(help_output)
    return help_output.getvalue()
