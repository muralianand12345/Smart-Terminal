"""
Interactive mode for SmartTerminal CLI.

This module handles the interactive command-line interface,
allowing users to continuously interact with the application.
"""

import os
import logging
from typing import Optional, Dict, Any

from smart_terminal.utils.colors import Colors
from smart_terminal.utils.helpers import print_banner, clear_screen

# Setup logging
logger = logging.getLogger(__name__)


async def run_interactive_mode(
    terminal: Any, config: Optional[Dict[str, Any]] = None, quiet: bool = False
) -> None:
    """
    Run SmartTerminal in interactive mode.

    Args:
        terminal: SmartTerminal instance
        config: Optional configuration dictionary
        quiet: Whether to suppress non-essential output
    """
    try:
        if not quiet:
            print_banner()
            print(Colors.highlight("SmartTerminal Interactive Mode"))
            print(Colors.info("Type 'exit' or 'quit' to exit, 'help' for help"))
            print(Colors.highlight("=============================="))

        # Check if shell integration is enabled and remind user
        if config and config.get("shell_integration_enabled", False):
            shell_integration = getattr(terminal, "shell_integration", None)
            if shell_integration and shell_integration.check_needs_sourcing():
                print(
                    Colors.info(
                        "\nThere are pending shell changes. To apply them, run: "
                        "source ~/.smartterminal/shell_history/last_commands.sh"
                    )
                )

        # Main interaction loop
        while True:
            try:
                # Display current directory in prompt
                cwd = os.getcwd()
                username = os.environ.get("USER", os.environ.get("USERNAME", "user"))

                # Prompt with current directory information
                user_input = input(
                    f"\n{Colors.info(f'{username}@{cwd}')} {Colors.cmd('st> ')}"
                )

                # Handle special commands
                if user_input.lower() in ["exit", "quit"]:
                    if not quiet:
                        print(Colors.info("Exiting SmartTerminal..."))
                    break

                elif user_input.lower() == "help":
                    show_interactive_help()
                    continue

                elif user_input.lower() == "clear":
                    clear_screen()
                    continue

                elif user_input.lower() == "history":
                    show_history(terminal)
                    continue

                elif user_input.lower() == "config":
                    show_config(config)
                    continue

                # Ignore empty input
                if not user_input.strip():
                    continue

                # Process the input
                await terminal.process_input(user_input)

            except KeyboardInterrupt:
                print(
                    "\n" + Colors.warning("Command interrupted. Type 'exit' to quit.")
                )
                continue

            except Exception as e:
                logger.error(f"Error in interactive mode: {e}", exc_info=True)
                print(Colors.error(f"An error occurred: {e}"))

    except KeyboardInterrupt:
        if not quiet:
            print("\n" + Colors.warning("Exiting..."))

    except Exception as e:
        logger.error(f"Error in interactive mode: {e}", exc_info=True)
        print(Colors.error(f"An error occurred: {e}"))


def show_interactive_help() -> None:
    """Show help information for interactive mode."""
    help_text = f"""
{Colors.highlight("SmartTerminal Interactive Mode Help")}
{Colors.highlight("=================================")}

{Colors.cmd("exit")}, {Colors.cmd("quit")}   Exit interactive mode
{Colors.cmd("help")}         Show this help message
{Colors.cmd("clear")}        Clear the screen
{Colors.cmd("history")}      Show command history
{Colors.cmd("config")}       Show current configuration

{Colors.highlight("Examples:")}
  {Colors.cmd("create a text file named example.txt with 'Hello World' content")}
  {Colors.cmd("list all files in the current directory sorted by size")}
  {Colors.cmd("find all python files containing the word 'import'")}
    """
    print(help_text)


def show_history(terminal: Any) -> None:
    """
    Show command history.

    Args:
        terminal: SmartTerminal instance
    """
    # Try to access history from terminal or directly from config
    try:
        # Get history
        from smart_terminal.config import ConfigManager

        history = ConfigManager.load_history()

        if not history:
            print(Colors.info("No command history."))
            return

        print(Colors.highlight("Command History"))
        print(Colors.highlight("==============="))

        # Filter to only show user messages (commands)
        user_messages = [msg for msg in history if msg.get("role") == "user"]

        for i, msg in enumerate(user_messages):
            print(f"{i + 1:2d}. {Colors.cmd(msg.get('content', ''))}")

    except Exception as e:
        logger.error(f"Error showing history: {e}")
        print(Colors.error(f"Error showing history: {e}"))


def show_config(config: Optional[Dict[str, Any]]) -> None:
    """
    Show current configuration.

    Args:
        config: Configuration dictionary
    """
    if not config:
        # Try to load config
        try:
            from smart_terminal.config import ConfigManager

            config = ConfigManager.load_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            print(Colors.error(f"Error loading config: {e}"))
            return

    print(Colors.highlight("Current Configuration"))
    print(Colors.highlight("====================="))

    # Group settings logically
    sections = {
        "General": ["default_os", "log_level"],
        "AI Service": ["api_key", "base_url", "model_name", "temperature"],
        "History": ["history_limit", "save_history"],
        "Shell": ["shell_integration_enabled", "auto_source_commands"],
    }

    # Function to redact sensitive values
    def redact_value(key: str, value: Any) -> str:
        if key == "api_key" and value:
            # Redact API key except first/last 4 chars if long enough
            if len(value) > 10:
                return f"{value[:4]}...{value[-4:]}"
            return "********"
        return str(value)

    # Print each section
    for section, keys in sections.items():
        print(f"\n{Colors.info(section)}:")
        for key in keys:
            if key in config:
                value = config[key]
                print(f"  {Colors.cmd(key)}: {redact_value(key, value)}")

    # Print custom settings
    custom_keys = [
        k
        for k in config
        if all(k not in section_keys for section_keys in sections.values())
    ]
    if custom_keys:
        print(f"\n{Colors.info('Custom Settings')}:")
        for key in custom_keys:
            print(f"  {Colors.cmd(key)}: {redact_value(key, config[key])}")
