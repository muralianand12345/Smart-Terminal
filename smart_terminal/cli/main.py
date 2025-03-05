"""
Main CLI entry point for SmartTerminal.

This module provides the main entry point for the command-line
interface, handling arguments, setup, and command execution.
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any

from smart_terminal import __version__
from smart_terminal.utils.colors import Colors
from smart_terminal.utils.logging import setup_logging
from smart_terminal.cli.interactive import run_interactive_mode
from smart_terminal.utils.helpers import print_error, print_banner
from smart_terminal.cli.arguments import parse_arguments, validate_args, get_help_text


# Setup logging
logger = logging.getLogger(__name__)


def run_setup(quiet: bool = False) -> bool:
    """
    Run the setup wizard for SmartTerminal.

    Args:
        quiet: Whether to suppress non-essential output

    Returns:
        bool: True if setup was successful, False otherwise
    """
    from smart_terminal.exceptions import ConfigError

    try:
        if not quiet:
            print_banner()
            print(Colors.highlight("SmartTerminal Setup"))
            print(Colors.highlight("=================="))

        # Load current config
        config = ConfigManager.load_config()

        # Get API key
        api_key = input(f"Enter your API key [{config.get('api_key', '')}]: ")
        if api_key:
            config["api_key"] = api_key

        # Get base URL
        base_url = input(
            f"Enter API base URL [{config.get('base_url', 'https://api.groq.com/openai/v1')}]: "
        )
        if base_url:
            config["base_url"] = base_url

        # Get model name
        model_name = input(
            f"Enter model name [{config.get('model_name', 'llama-3.3-70b-versatile')}]: "
        )
        if model_name:
            config["model_name"] = model_name

        # Get default OS
        default_os = input(
            f"Enter default OS (macos, linux, windows) [{config.get('default_os', 'macos')}]: "
        )
        if default_os and default_os in ["macos", "linux", "windows"]:
            config["default_os"] = default_os

        # Get history limit
        history_limit_str = input(
            f"Enter history limit [{config.get('history_limit', 20)}]: "
        )
        if history_limit_str:
            try:
                history_limit = int(history_limit_str)
                config["history_limit"] = history_limit
            except ValueError:
                print(Colors.warning("Invalid history limit. Using previous value."))

        # Get log level
        log_level = input(
            f"Enter log level (DEBUG, INFO, WARNING, ERROR) [{config.get('log_level', 'INFO')}]: "
        )
        if log_level and log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            config["log_level"] = log_level

        # Ask about shell integration
        enable_shell_integration = input(
            f"Enable shell integration (y/n) [{config.get('shell_integration_enabled', False) and 'y' or 'n'}]: "
        ).lower()
        if enable_shell_integration == "y":
            config["shell_integration_enabled"] = True
            setup_shell_integration()
        elif enable_shell_integration == "n":
            config["shell_integration_enabled"] = False

        # Save configuration
        ConfigManager.save_config(config)
        print(Colors.success("Configuration saved."))

        return True

    except ConfigError as e:
        print_error(str(e))
        return False
    except Exception as e:
        print_error(f"Setup failed: {e}")
        return False


def setup_shell_integration() -> bool:
    """
    Set up shell integration for environment-changing commands.

    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        print(Colors.highlight("\nShell Integration Setup"))
        print(Colors.highlight("====================="))

        # Try to import ShellAdapterFactory
        try:
            from smart_terminal.adapters.shell import ShellAdapterFactory

            # Create appropriate shell adapter
            shell_adapter = ShellAdapterFactory.create_adapter()

            # Show info about shell integration
            print(
                Colors.info(
                    "Shell integration allows SmartTerminal to modify your shell environment "
                    "(like changing directories or setting environment variables)."
                )
            )

            # Display integration script
            print(
                Colors.info(
                    "\nTo enable shell integration, you need to add the following to your shell config file:"
                )
            )
            print(shell_adapter.get_integration_script())

            # Auto-setup check
            shell_type = shell_adapter.shell_type
            if shell_type == "bash":
                config_file = "~/.bashrc"
            elif shell_type == "zsh":
                config_file = "~/.zshrc"
            elif shell_type == "powershell":
                config_file = "$PROFILE"
            else:
                config_file = "your shell configuration file"

            print(
                Colors.info(
                    f"\nAdd this to {config_file} and restart your shell or source the file."
                )
            )

            # Ask if user wants to automatically add to config
            auto_setup = input(
                Colors.warning(
                    f"Would you like to automatically add this to {config_file}? (y/n): "
                )
            ).lower()

            if auto_setup == "y":
                import os

                config_path = os.path.expanduser(config_file)

                # Check if the file exists
                if os.path.exists(config_path):
                    # Read the current content
                    with open(config_path, "r") as f:
                        content = f.read()

                    # Check if shell integration is already there
                    if "smart_terminal_integration" in content:
                        print(
                            Colors.warning(
                                "Shell integration is already set up in your config file."
                            )
                        )
                    else:
                        # Append to the file
                        with open(config_path, "a") as f:
                            f.write("\n# Added by SmartTerminal setup\n")
                            f.write(shell_adapter.get_integration_script())

                        print(
                            Colors.success(f"Shell integration added to {config_file}")
                        )
                        print(Colors.info(f"To activate it, run: source {config_file}"))
                else:
                    print(
                        Colors.error(
                            f"Config file {config_file} not found. Please add the shell integration manually."
                        )
                    )

            # Create a test commands file for verification
            test_commands = [
                "echo 'Shell integration is working!'",
                'cd "$(pwd)"',  # This will just cd to the current directory as a test
            ]

            shell_adapter.write_environment_command(
                test_commands, "Test shell integration"
            )
            print(
                Colors.info(
                    "\nA test command file has been created. To test your setup:"
                )
            )
            print(
                Colors.info(
                    "1. First, restart your terminal or source your shell config file"
                )
            )
            print(
                Colors.info(
                    "2. Then run: source ~/.smartterminal/shell_history/last_commands.sh"
                )
            )

            return True

        except ImportError:
            print_error("Shell adapter module not available.")
            return False

    except Exception as e:
        print_error(f"Shell integration setup failed: {e}")
        return False


async def run_single_command(
    command: str,
    config: Dict[str, Any],
    dry_run: bool = False,
    json_output: bool = False,
    bypass_cache: bool = False,
    clear_cache: bool = False,
) -> bool:
    """
    Run a single command through SmartTerminal.

    Args:
        command: Natural language command to execute
        config: Configuration dictionary
        dry_run: Whether to only show commands without executing them
        json_output: Whether to output results in JSON format
        bypass_cache: Whether to bypass cache and force new generation
        clear_cache: Whether to clear cache before execution

    Returns:
        bool: True if command was executed successfully, False otherwise
    """
    try:
        # Import necessary classes
        try:
            from smart_terminal.core import SmartTerminal
            from smart_terminal.exceptions import AIError, CommandError

        except ImportError:
            # Legacy imports
            from smart_terminal.terminal import SmartTerminal
            from smart_terminal.ai import AIError
            from smart_terminal.commands import CommandError

        # Initialize SmartTerminal with config
        terminal = SmartTerminal()

        # If dry_run is enabled, set the mode
        if dry_run:
            # Set dry run mode if available
            if hasattr(terminal, "set_dry_run"):
                terminal.set_dry_run(True)
            else:
                print(Colors.warning("Dry run mode not supported in this version."))

        # If json_output is enabled, set the mode
        if json_output:
            # Set JSON output mode if available
            if hasattr(terminal, "set_json_output"):
                terminal.set_json_output(True)
            else:
                print(Colors.warning("JSON output not supported in this version."))

        # Handle cache-related options
        if (
            clear_cache
            and hasattr(terminal, "ai_client")
            and hasattr(terminal.ai_client, "cache_manager")
            and terminal.ai_client.cache_manager
        ):
            terminal.ai_client.cache_manager.clear_cache()
            if not json_output:
                print(Colors.info("Command cache cleared."))

        # Execute the command
        if hasattr(terminal, "run_command"):
            await terminal.run_command(command)
        else:
            # Legacy method
            await terminal.process_input(command, bypass_cache=bypass_cache)

        return True

    except AIError as e:
        print_error(str(e))
        return False

    except CommandError as e:
        print_error(str(e))
        return False

    except Exception as e:
        print_error(f"An error occurred: {e}")
        return False


def show_version_info(json_output: bool = False) -> None:
    """
    Display version information.

    Args:
        json_output: Whether to output in JSON format
    """
    import platform

    if json_output:
        info = {
            "version": __version__,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "processor": platform.processor(),
        }
        print(json.dumps(info, indent=2))
    else:
        print(f"{Colors.highlight('SmartTerminal')} version {Colors.cmd(__version__)}")
        print(f"Python {platform.python_version()} on {platform.platform()}")


def show_cache_info(json_output: bool = False) -> None:
    """
    Display command cache information.

    Args:
        json_output: Whether to output in JSON format
    """
    try:
        # Try to import cache manager
        try:
            from smart_terminal.cache.manager import CacheManager
            from smart_terminal.config import ConfigManager

            # Load config to get cache settings
            config = ConfigManager.load_config()
            cache_config = {k: v for k, v in config.items() if k.startswith("cache_")}

            # Create cache manager
            cache_manager = CacheManager(cache_config)

            # Get statistics
            stats = cache_manager.get_statistics()

            if json_output:
                print(json.dumps(stats, indent=2))
            else:
                print(Colors.highlight("Command Cache Statistics"))
                print(Colors.highlight("======================="))

                print(f"{Colors.info('Enabled:')} {Colors.cmd(str(stats['enabled']))}")
                print(f"{Colors.info('Entries:')} {Colors.cmd(str(stats['entries']))}")
                print(
                    f"{Colors.info('Maximum entries:')} {Colors.cmd(str(stats['max_entries']))}"
                )
                print(
                    f"{Colors.info('Maximum age (days):')} {Colors.cmd(str(stats['max_age_days']))}"
                )

                # Convert bytes to human-readable format
                size_bytes = stats["size_bytes"]
                if size_bytes < 1024:
                    size_str = f"{size_bytes} bytes"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.2f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

                print(f"{Colors.info('Cache file size:')} {Colors.cmd(size_str)}")
                print(
                    f"{Colors.info('Hit rate:')} {Colors.cmd(f'{stats["hit_rate"] * 100:.2f}%')}"
                )

                # Show cache file location
                print(f"\n{Colors.info('Cache File Location:')}")
                print(f"  {CacheManager.CACHE_FILE}")

                # Show cache management commands
                print(f"\n{Colors.info('Cache Management Commands:')}")
                print(f"  {Colors.cmd('st --clear-cache')} - Clear the entire cache")
                print(
                    f"  {Colors.cmd('st --no-cache "your command"')} - Bypass cache for a single command"
                )

        except ImportError:
            print_error("Cache manager module not available")

    except Exception as e:
        print_error(f"Error retrieving cache information: {e}")


def main() -> int:
    """
    Main entry point for the SmartTerminal CLI.

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        # Parse arguments
        args = parse_arguments()

        # Show version and exit
        if args.version:
            show_version_info(args.json)
            return 0

        # Show config info and exit
        if args.config_info:
            show_config_info(args.json)
            return 0

        # Show cache info and exit
        if args.cache_info:
            show_cache_info(args.json)
            return 0

        # Initialize basic logging
        log_level = "DEBUG" if args.debug else "INFO"
        setup_logging(log_level, log_to_console=not args.quiet)

        # Validate arguments
        if not validate_args(args):
            print_error("Invalid argument combination")
            print(get_help_text())
            return 1

        # Clear history
        if args.clear_history:
            try:
                ConfigManager.reset_history()
                if not args.quiet:
                    print(Colors.success("Command history cleared."))
                return 0
            except Exception as e:
                print_error(f"Failed to clear history: {e}")
                return 1

        # Initialize configuration
        try:
            ConfigManager.init_config()
        except Exception as e:
            print_error(f"Configuration error: {e}")
            return 1

        # Load configuration
        config = ConfigManager.load_config()

        # Override config with command-line options
        if args.api_key:
            config["api_key"] = args.api_key
        if args.model:
            config["model_name"] = args.model
        if args.base_url:
            config["base_url"] = args.base_url
        if args.os:
            config["default_os"] = args.os

        # Setup command
        if args.setup:
            success = run_setup(args.quiet)
            return 0 if success else 1

        # Shell setup command
        if args.shell_setup:
            success = setup_shell_integration()
            return 0 if success else 1

        # Check if API key is set
        if not config.get("api_key"):
            print_error("API key not set. Please run 'st --setup' to configure.")
            return 1

        # Import necessary classes
        try:
            from smart_terminal.core import SmartTerminal
        except ImportError:
            # Legacy import
            from smart_terminal.terminal import SmartTerminal

        # Initialize SmartTerminal
        terminal = SmartTerminal()

        # Interactive mode
        if args.interactive:
            asyncio.run(run_interactive_mode(terminal, config, args.quiet))
            return 0

        # Clear cache if requested
        if args.clear_cache:
            try:
                # Import cache manager directly
                try:
                    from smart_terminal.cache.manager import CacheManager

                    cache_manager = CacheManager(config)
                    cache_manager.clear_cache()
                    if not args.quiet:
                        print(Colors.success("Command cache cleared."))
                except ImportError:
                    print_error("Cache manager not available. Unable to clear cache.")
                    return 1

                if args.command is None:  # If only clearing cache, return success
                    return 0
            except Exception as e:
                print_error(f"Failed to clear cache: {e}")
                return 1

        # Process a single command
        if args.command:
            success = asyncio.run(
                run_single_command(
                    args.command,
                    config,
                    dry_run=args.dry_run,
                    json_output=args.json,
                    bypass_cache=args.no_cache,
                    clear_cache=args.clear_cache,
                )
            )
            return 0 if success else 1

    except KeyboardInterrupt:
        print("\n" + Colors.warning("Operation cancelled by user."))
        return 0
    except Exception as e:
        print_error(f"An error occurred: {e}")
        return 1


def run_cli() -> None:
    """Entry point for setuptools console_scripts."""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
