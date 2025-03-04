"""
Command Line Interface for SmartTerminal.

This module handles the command-line interface, argument parsing,
and the main entry point for the application.
"""

import sys
import asyncio
import argparse
import logging

from smart_terminal import __version__
from smart_terminal.config import ConfigManager, ConfigError
from smart_terminal.terminal import SmartTerminal
from smart_terminal.utils import Colors, setup_logging, print_error

# Setup logging
logger = logging.getLogger("smartterminal.cli")


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="SmartTerminal - Natural language to terminal commands"
    )
    parser.add_argument(
        "command", nargs="?", help="Natural language command to execute"
    )
    parser.add_argument(
        "--setup", action="store_true", help="Setup SmartTerminal configuration"
    )
    parser.add_argument(
        "--clear-history", action="store_true", help="Clear command history"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--version", "-v", action="store_true", help="Show version information"
    )

    return parser.parse_args()


def run_setup(terminal: SmartTerminal) -> None:
    """
    Run the setup wizard for SmartTerminal.

    Args:
        terminal (SmartTerminal): Initialized SmartTerminal instance.
    """
    try:
        terminal.setup()
    except ConfigError as e:
        print_error(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in setup: {e}", exc_info=True)
        print_error(f"Setup failed: {e}")


async def run_interactive_mode(terminal: SmartTerminal) -> None:
    """
    Run SmartTerminal in interactive mode.

    Args:
        terminal (SmartTerminal): Initialized SmartTerminal instance.
    """
    try:
        await terminal.run_interactive()
    except KeyboardInterrupt:
        print("\n" + Colors.warning("Exiting..."))
    except Exception as e:
        logger.error(f"Error in interactive mode: {e}", exc_info=True)
        print_error(f"An error occurred: {e}")


async def run_single_command(terminal: SmartTerminal, command: str) -> None:
    """
    Run a single command through SmartTerminal.

    Args:
        terminal (SmartTerminal): Initialized SmartTerminal instance.
        command (str): The natural language command to process.
    """
    try:
        await terminal.run_command(command)
    except Exception as e:
        logger.error(f"Error executing command: {e}", exc_info=True)
        print_error(f"An error occurred: {e}")


def main() -> int:
    """
    Main entry point for the SmartTerminal CLI.

    Returns:
        int: Exit code (0 for success, non-zero for error).
    """
    try:
        # Parse arguments
        args = parse_arguments()

        # Show version and exit
        if args.version:
            print(Colors.highlight(f"SmartTerminal v{__version__}"))
            return 0

        # Initialize basic logging
        log_level = "DEBUG" if args.debug else "INFO"
        setup_logging(log_level)

        # Clear history
        if args.clear_history:
            ConfigManager.reset_history()
            print(Colors.success("Command history cleared."))
            return 0

        # Initialize configuration
        try:
            ConfigManager.init_config()
        except ConfigError as e:
            print_error(f"Configuration error: {e}")
            return 1

        # Initialize SmartTerminal
        terminal = SmartTerminal()

        # Setup command
        if args.setup:
            run_setup(terminal)
            return 0

        # Check if API key is set
        config = ConfigManager.load_config()
        if not config.get("api_key"):
            print(
                Colors.warning("API key not set. Please run 'st --setup' to configure.")
            )
            return 1

        # Interactive mode
        if args.interactive:
            asyncio.run(run_interactive_mode(terminal))
            return 0

        # Process a single command
        if args.command:
            asyncio.run(run_single_command(terminal, args.command))
            return 0
        else:
            # No command provided, show help
            parser = argparse.ArgumentParser(
                description="SmartTerminal - Natural language to terminal commands"
            )
            parser.add_argument(
                "command", nargs="?", help="Natural language command to execute"
            )
            parser.add_argument(
                "--setup", action="store_true", help="Setup SmartTerminal configuration"
            )
            parser.add_argument(
                "--clear-history", action="store_true", help="Clear command history"
            )
            parser.add_argument(
                "--interactive",
                "-i",
                action="store_true",
                help="Run in interactive mode",
            )
            parser.add_argument(
                "--debug", action="store_true", help="Enable debug logging"
            )
            parser.add_argument(
                "--version", "-v", action="store_true", help="Show version information"
            )
            parser.print_help()
            return 0

    except KeyboardInterrupt:
        print("\n" + Colors.warning("Operation cancelled by user."))
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        print_error(f"An error occurred: {e}")
        return 1


def run_cli():
    """Entry point for setuptools console_scripts."""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
