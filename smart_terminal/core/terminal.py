"""
Main SmartTerminal class implementation.

This module provides the core SmartTerminal class that orchestrates
the command generation and execution process, manages user interaction,
and maintains conversation history.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union

from smart_terminal.core.ai import AIClient
from smart_terminal.core.base import TerminalInterface
from smart_terminal.core.context import ContextGenerator
from smart_terminal.core.shell_integration import ShellIntegration
from smart_terminal.core.commands import CommandGenerator, CommandExecutor
from smart_terminal.config import ConfigManager
from smart_terminal.exceptions import (
    SmartTerminalError,
    AIError,
    ConfigError,
)
from smart_terminal.utils.colors import Colors
from smart_terminal.utils.helpers import (
    print_error,
    print_banner,
    print_warning,
    print_success,
    print_info,
)

# Import adapters if available
try:
    from smart_terminal.adapters.shell import ShellAdapterFactory, ShellAdapter
    from smart_terminal.adapters.ai_provider import AIProviderFactory

    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False

# Import models if available
try:
    from smart_terminal.models.command import Command, CommandResult
    from smart_terminal.models.message import (
        Message,
        UserMessage,
        AIMessage,
        SystemMessage,
    )
    from smart_terminal.models.config import Config
    from smart_terminal.models.context import ContextData

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)


class SmartTerminal(TerminalInterface):
    """
    Main class for the SmartTerminal application.

    This class orchestrates the command generation and execution process,
    manages user interaction, and maintains conversation history.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SmartTerminal with configuration and components.

        Args:
            config: Optional configuration dictionary (if not provided, will be loaded)
        """
        try:
            # Load configuration if not provided
            if config is None:
                config = ConfigManager.load_config()

            self.config = config
            self.current_directory = os.getcwd()

            # Initialize settings
            self.dry_run = False
            self.json_output = False

            # Initialize shell integration
            self.shell_integration = ShellIntegration()

            # Try to use shell adapter if available
            if ADAPTERS_AVAILABLE:
                try:
                    self.shell_adapter = ShellAdapterFactory.create_adapter()
                    logger.debug(
                        f"Using shell adapter: {self.shell_adapter.shell_type}"
                    )
                except Exception as e:
                    logger.debug(f"Failed to create shell adapter: {e}")
                    self.shell_adapter = None
            else:
                self.shell_adapter = None
                logger.debug("Shell adapters not available")

            # Extract cache configuration
            cache_config = {
                "cache_enabled": config.get("cache_enabled", True),
                "cache_max_entries": config.get("cache_max_entries", 1000),
                "cache_max_age_days": config.get("cache_max_age_days", 30),
                "cache_min_similarity": config.get("cache_min_similarity", 0.85),
                "cache_fuzzy_matching": config.get("cache_fuzzy_matching", True),
            }

            # Initialize AI client
            self.ai_client = AIClient(
                api_key=config.get("api_key", ""),
                base_url=config.get("base_url", "https://api.groq.com/openai/v1"),
                model_name=config.get("model_name", "llama-3.3-70b-versatile"),
                temperature=config.get("temperature", 0.0),
                cache_config=cache_config,
            )

            # Initialize command generator
            self.command_generator = CommandGenerator(self.ai_client)

            # Initialize command executor
            self.command_executor = CommandExecutor(dry_run=self.dry_run)

            # Initialize context generator
            self.context_generator = ContextGenerator(
                max_history=config.get("history_limit", 5)
            )

        except Exception as e:
            raise SmartTerminalError(f"Failed to initialize SmartTerminal: {e}")

    def set_dry_run(self, enabled: bool) -> None:
        """
        Set dry run mode (show commands without executing them).

        Args:
            enabled: Whether to enable dry run mode
        """
        self.dry_run = enabled

        # Update command executor
        if hasattr(self, "command_executor"):
            self.command_executor.dry_run = enabled

    def set_json_output(self, enabled: bool) -> None:
        """
        Set JSON output mode.

        Args:
            enabled: Whether to enable JSON output
        """
        self.json_output = enabled

    async def process_input(
        self, user_query: str, bypass_cache: bool = False
    ) -> Union[bool, Dict[str, Any]]:
        """
        Process user input, generate and execute commands.

        Args:
            user_query: Natural language query from user
            bypass_cache: Whether to bypass the cache and force a new command generation

        Returns:
            Result of processing (success status or result data)
        """
        if not self.json_output:
            print_info(f"Processing: {user_query}")

        self.current_directory = os.getcwd()

        # Generate enhanced context
        context = self.context_generator.generate_context()

        # Add context to the query
        context_prompt = self.context_generator.get_context_prompt()
        enhanced_query = (
            f"[CONTEXT]\n{context_prompt}\n[/CONTEXT]\n\nUser Query: {user_query}"
        )

        logger.debug(f"Enhanced query with context: {enhanced_query}")

        try:
            # Get commands using the enhanced query
            commands = await self.command_generator.generate_commands(
                enhanced_query, context=context, bypass_cache=bypass_cache
            )

            # No commands returned
            if not commands or len(commands) == 0:
                if not self.json_output:
                    print_warning("Sorry, I couldn't determine the commands needed.")
                return False

            # If in JSON output mode, just return the commands
            if self.json_output:
                return {"success": True, "commands": commands}

            # Check for shell-affecting commands
            environment_changing_commands = ["cd ", "export ", "="]
            env_changing_cmds = []

            # Identify environment-changing commands
            for cmd in commands:
                cmd_str = cmd.get("command", "").strip()
                if any(
                    cmd_str.startswith(prefix)
                    for prefix in environment_changing_commands
                ):
                    env_changing_cmds.append(cmd_str)

            has_environment_changing_commands = len(env_changing_cmds) > 0
            shell_integration_enabled = self.config.get(
                "shell_integration_enabled", False
            )
            auto_source_commands = self.config.get("auto_source_commands", False)

            # Check if shell integration is actually working
            if shell_integration_enabled:
                shell_integration_working = (
                    self.shell_integration.is_shell_integration_active()
                )
            else:
                shell_integration_working = False

            # If environment-changing commands are present but shell integration is not enabled or not working
            if has_environment_changing_commands and not shell_integration_enabled:
                print_warning(
                    "Note: Some commands may modify your shell environment (like changing directories)."
                )
                print_warning(
                    "These changes won't persist in your actual terminal unless you set up shell integration."
                )
                setup_now = (
                    input(
                        Colors.warning("Set up shell integration now? (y/n): ")
                    ).lower()
                    == "y"
                )

                if setup_now:
                    self.setup_shell_integration()
                    shell_integration_enabled = True
                    self.config["shell_integration_enabled"] = True
                    ConfigManager.save_config(self.config)

            # Execute commands
            success = self.command_executor.process_commands(commands)

            # Update command history
            self.save_to_history(user_query, commands)

            # Handle shell integration for environment-changing commands
            if has_environment_changing_commands and shell_integration_enabled:
                # Create the shell integration command file
                description = f"Commands from: {user_query}"
                self.shell_integration.write_shell_commands(
                    env_changing_cmds, description
                )

                # Inform user about shell integration
                if not shell_integration_working or not auto_source_commands:
                    print_info(
                        "\nTo apply environment changes to your parent shell, run: "
                        "source ~/.smartterminal/shell_history/last_commands.sh"
                    )

            return success

        except AIError as e:
            print_error(str(e))
            return False
        except Exception as e:
            print_error(f"An unexpected error occurred: {e}")
            return False

    async def run_command(
        self, command: str, bypass_cache: bool = False
    ) -> Union[bool, Dict[str, Any]]:
        """
        Run a single command through SmartTerminal.

        Args:
            command: Natural language command to process
            bypass_cache: Whether to bypass cache and force new generation

        Returns:
            Result of command execution
        """
        # Load chat history
        chat_history = ConfigManager.load_history()

        # Process the command
        result = await self.process_input(command, bypass_cache=bypass_cache)

        return result

    async def run_interactive(self) -> None:
        """
        Run SmartTerminal in interactive mode.
        """
        print_banner()
        print(Colors.highlight("SmartTerminal Interactive Mode"))
        print_info("Type 'exit' or 'quit' to exit")
        print(Colors.highlight("=============================="))

        # Check if shell integration is enabled and remind user
        if (
            self.config.get("shell_integration_enabled", False)
            and self.shell_integration.check_needs_sourcing()
        ):
            print_info(
                "\nThere are pending shell changes. To apply them, run: "
                "source ~/.smartterminal/shell_history/last_commands.sh"
            )

        # Load chat history
        history = ConfigManager.load_history()

        # Main interaction loop
        while True:
            try:
                # Display current directory in prompt
                cwd = os.getcwd()
                username = os.environ.get("USER", os.environ.get("USERNAME", "user"))

                user_input = input(
                    f"\n{Colors.info(f'{username}@{cwd}')} {Colors.cmd('st> ')}"
                )

                # Handle special commands
                if user_input.lower() in ["exit", "quit"]:
                    break

                if user_input.lower() == "help":
                    self._show_interactive_help()
                    continue

                if user_input.lower() == "clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    continue

                if user_input.lower() == "history":
                    self._show_history(history)
                    continue

                if not user_input:
                    continue

                # Process the input
                await self.process_input(user_input)

                # Add to history
                history.append({"role": "user", "content": user_input})

                # Save history
                ConfigManager.save_history(history)

            except KeyboardInterrupt:
                print("\n" + Colors.warning("Exiting..."))
                break
            except Exception as e:
                print_error(f"An error occurred: {e}")

    def _show_interactive_help(self) -> None:
        """Show help information for interactive mode."""
        help_text = f"""
{Colors.highlight("SmartTerminal Interactive Mode Help")}
{Colors.highlight("=================================")}

{Colors.cmd("exit")}, {Colors.cmd("quit")}   Exit interactive mode
{Colors.cmd("help")}         Show this help message
{Colors.cmd("clear")}        Clear the screen
{Colors.cmd("history")}      Show command history

{Colors.highlight("Examples:")}
  {Colors.cmd("create a text file named example.txt with 'Hello World' content")}
  {Colors.cmd("list all files in the current directory sorted by size")}
  {Colors.cmd("find all python files containing the word 'import'")}
    """
        print(help_text)

    def _show_history(self, history: List[Dict[str, Any]]) -> None:
        """
        Show command history.

        Args:
            history: Chat history
        """
        if not history:
            print_info("No command history.")
            return

        print(Colors.highlight("Command History"))
        print(Colors.highlight("==============="))

        # Filter to only show user messages (commands)
        user_messages = [msg for msg in history if msg.get("role") == "user"]

        for i, msg in enumerate(user_messages):
            print(f"{i + 1:2d}. {Colors.cmd(msg.get('content', ''))}")

    def setup(self) -> bool:
        """
        Run the setup process to configure SmartTerminal.

        Returns:
            True if setup was successful, False otherwise
        """
        print_banner()
        print(Colors.highlight("SmartTerminal Setup"))
        print(Colors.highlight("=================="))

        try:
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
                    print_warning("Invalid history limit. Using previous value.")

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
                self.setup_shell_integration()
            elif enable_shell_integration == "n":
                config["shell_integration_enabled"] = False

            # Save configuration
            ConfigManager.save_config(config)
            print_success("Configuration saved.")

            return True

        except ConfigError as e:
            print_error(str(e))
            return False
        except Exception as e:
            print_error(f"Setup failed: {e}")
            return False

    def setup_shell_integration(self) -> bool:
        """
        Set up shell integration for environment-changing commands.

        Returns:
            True if setup was successful, False otherwise
        """
        try:
            print(Colors.highlight("\nShell Integration Setup"))
            print(Colors.highlight("====================="))

            print_info(
                "Shell integration allows SmartTerminal to modify your shell environment "
                "(like changing directories or setting environment variables)."
            )

            # Display instructions
            print_info(
                "\nTo enable shell integration, you need to add the following to your shell config file:"
            )
            print(self.shell_integration.get_shell_integration_script())

            # Determine config file
            shell_type = os.environ.get("SHELL", "")
            if "zsh" in shell_type:
                config_file = "~/.zshrc"
            elif "bash" in shell_type:
                config_file = "~/.bashrc"
            else:
                config_file = "your shell configuration file"

            print_info(
                f"\nAdd this to {config_file} and restart your shell or source the file."
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
                        print_warning(
                            "Shell integration is already set up in your config file."
                        )
                    else:
                        # Append to the file
                        with open(config_path, "a") as f:
                            f.write("\n# Added by SmartTerminal setup\n")
                            f.write(
                                self.shell_integration.get_shell_integration_script()
                            )

                        print_success(f"Shell integration added to {config_file}")
                        print_info(f"To activate it, run: source {config_file}")
                else:
                    print_error(
                        f"Config file {config_file} not found. Please add the shell integration manually."
                    )

            # Create a test commands file
            test_commands = [
                "echo 'Shell integration is working!'",
                'cd "$(pwd)"',  # This will just cd to the current directory as a test
            ]

            self.shell_integration.write_shell_commands(
                test_commands, "Test shell integration"
            )
            print_info("\nA test command file has been created. To test your setup:")
            print_info(
                "1. First, restart your terminal or source your shell config file"
            )
            print_info(
                "2. Then run: source ~/.smartterminal/shell_history/last_commands.sh"
            )

            return True

        except Exception as e:
            print_error(f"Shell integration setup failed: {e}")
            return False

    def save_to_history(self, user_query: str, commands: List[Dict[str, Any]]) -> None:
        """
        Save the current interaction to history.

        Args:
            user_query: User's natural language query
            commands: Generated commands
        """
        try:
            # Load existing history
            history = ConfigManager.load_history()

            # Add user message
            history.append({"role": "user", "content": user_query})

            # Add assistant message with commands
            assistant_content = "I executed the following commands:\n"
            for cmd in commands:
                command_str = cmd.get("command", "")
                assistant_content += f"- {command_str}\n"

            history.append({"role": "assistant", "content": assistant_content})

            # Save updated history
            ConfigManager.save_history(history)

            # Update context generator with latest command
            if commands and len(commands) > 0:
                latest_cmd = commands[-1]
                command_str = latest_cmd.get("command", "")
                self.context_generator.update_context(command_str, "")

        except Exception as e:
            logger.error(f"Error saving to history: {e}")
            # Don't raise an exception for history saving failures
            # as it's not critical to the operation

    def get_version(self) -> str:
        """
        Get the version of SmartTerminal.

        Returns:
            str: Version string
        """
        try:
            from smart_terminal import __version__

            return __version__
        except ImportError:
            return "unknown"

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about SmartTerminal usage.

        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        stats = {
            "version": self.get_version(),
            "config_path": str(ConfigManager.CONFIG_FILE),
            "history_count": len(ConfigManager.load_history()),
            "shell_integration": self.config.get("shell_integration_enabled", False),
            "shell_integration_active": self.shell_integration.is_shell_integration_active()
            if self.config.get("shell_integration_enabled", False)
            else False,
        }

        return stats
