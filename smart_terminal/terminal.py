"""
Main SmartTerminal class implementation.

This module provides the core SmartTerminal class that orchestrates
the command generation and execution process, manages user interaction,
and maintains conversation history.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

from smart_terminal.ai import AIClient, AIError
from smart_terminal.commands import CommandGenerator, CommandExecutor
from smart_terminal.config import ConfigManager, ConfigError
from smart_terminal.utils import Colors, print_error, print_banner
from smart_terminal.context import ContextGenerator
from smart_terminal.shell_integration import ShellIntegration

# Setup logging
logger = logging.getLogger("smartterminal.terminal")


class SmartTerminal:
    """
    Main class for the SmartTerminal application.

    This class orchestrates the command generation and execution process,
    manages user interaction, and maintains conversation history.
    """

    def __init__(self):
        """Initialize SmartTerminal with configuration and components."""
        try:
            # Load configuration
            config = ConfigManager.load_config()
            logger.debug("Initializing SmartTerminal")

            self.current_directory = os.getcwd()

            # Track recent commands for context
            self.recent_commands = []
            self.recent_outputs = []
            self.max_context_items = 5

            # Initialize shell integration
            self.shell_integration = ShellIntegration()

            # Initialize AI client
            self.ai_client = AIClient(
                api_key=config.get("api_key", ""),
                base_url=config.get("base_url", "https://api.groq.com/openai/v1"),
                model_name=config.get("model_name", "llama-3.3-70b-versatile"),
            )

            # Initialize command generator
            self.command_generator = CommandGenerator(self.ai_client)

        except Exception as e:
            logger.error(f"Failed to initialize SmartTerminal: {e}")
            print_error(f"Failed to initialize SmartTerminal: {e}")
            raise

    async def process_input(
        self, user_query: str, chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process user input, generate and execute commands.

        Args:
            user_query (str): Natural language query from user.
            chat_history (Optional[List[Dict[str, Any]]]): Previous chat history for context.

        Returns:
            List[Dict[str, Any]]: Updated chat history after command execution.
        """
        print(Colors.info(f"Processing: {user_query}"))

        self.current_directory = os.getcwd()

        # Generate enhanced context
        context_prompt = ContextGenerator.get_context_prompt()

        # Add context to the query
        enhanced_query = (
            f"[CONTEXT]\n{context_prompt}\n[/CONTEXT]\n\nUser Query: {user_query}"
        )

        logger.debug(f"Enhanced query with context: {enhanced_query}")

        # Initialize or use provided chat history
        if chat_history is None:
            chat_history = []

        # Add user query to history (the original query without context)
        chat_history.append({"role": "user", "content": user_query})

        try:
            # Get commands using the enhanced query
            command_sets = await self.command_generator.generate_commands(
                enhanced_query, chat_history
            )

            # No commands returned
            if not command_sets or len(command_sets) == 0:
                print(
                    Colors.warning("Sorry, I couldn't determine the commands needed.")
                )
                return chat_history

            # Extract the commands
            commands = []
            for command_set in command_sets:
                for cmd in command_set:
                    try:
                        args = json.loads(cmd.function.arguments)
                        commands.append(args)
                    except Exception as e:
                        logger.error(f"Error parsing command: {e}")
                        print_error(f"Error parsing command: {cmd}")

            # If no valid commands found
            if len(commands) == 0:
                print(Colors.warning("Sorry, I couldn't generate valid commands."))
                return chat_history

            # Check for shell-affecting commands
            environment_changing_commands = ["cd ", "export ", "="]
            has_environment_changing_commands = any(
                cmd.get("command", "").strip().startswith(prefix)
                for cmd in commands
                for prefix in environment_changing_commands
            )

            config = ConfigManager.load_config()
            shell_integration_enabled = config.get("shell_integration_enabled", False)

            # Check if shell integration is actually working
            if shell_integration_enabled:
                shell_integration_working = (
                    self.shell_integration.is_shell_integration_active()
                )
            else:
                shell_integration_working = False

            # If environment-changing commands are present but shell integration is not enabled or not working
            if has_environment_changing_commands and not shell_integration_enabled:
                print(
                    Colors.warning(
                        "Note: Some commands may modify your shell environment (like changing directories)."
                    )
                )
                print(
                    Colors.warning(
                        "These changes won't persist in your actual terminal unless you set up shell integration."
                    )
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
                    config["shell_integration_enabled"] = True
                    ConfigManager.save_config(config)

            # Process and execute commands
            CommandExecutor.process_commands(commands)

            # Update chat history with executed commands
            assistant_content = "I executed the following commands:\n"
            for cmd in commands:
                assistant_content += f"- {cmd.get('command', '')}\n"

            chat_history.append({"role": "assistant", "content": assistant_content})

            # Trim history if needed
            history_limit = config.get("history_limit", 20)
            if len(chat_history) > history_limit:
                chat_history = chat_history[-history_limit:]

            # Track command execution for future context
            if commands and len(commands) > 0:
                for cmd in commands:
                    command = cmd.get("command", "")
                    self.recent_commands.append(command)
                    # Keep only the most recent commands
                    if len(self.recent_commands) > self.max_context_items:
                        self.recent_commands.pop(0)

            # Only display reminder about shell integration if:
            # 1. There are environment-changing commands
            # 2. Shell integration is enabled in config but not actually working
            # 3. There's a marker file indicating commands need to be sourced
            if (
                has_environment_changing_commands
                and shell_integration_enabled
                and not shell_integration_working
                and self.shell_integration.check_needs_sourcing()
            ):
                print(
                    Colors.info(
                        "\nTo apply environment changes to your parent shell, run: "
                        "source ~/.smartterminal/shell_history/last_commands.sh"
                    )
                )

            return chat_history

        except AIError as e:
            print_error(str(e))
            logger.error(f"AI error during command processing: {e}")
            return chat_history
        except Exception as e:
            print_error(f"An unexpected error occurred: {e}")
            logger.error(f"Unexpected error in process_input: {e}", exc_info=True)
            return chat_history

    def setup(self) -> None:
        """Run the setup process to configure SmartTerminal."""
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
                    print(
                        Colors.warning("Invalid history limit. Using previous value.")
                    )

            # Get log level
            log_level = input(
                f"Enter log level (DEBUG, INFO, WARNING, ERROR) [{config.get('log_level', 'INFO')}]: "
            )
            if log_level and log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                config["log_level"] = log_level

            # Ask about shell integration
            enable_shell_integration = input(
                f"Enable shell integration (y/n) [{config.get('shell_integration_enabled', 'n')}]: "
            ).lower()
            if enable_shell_integration == "y":
                config["shell_integration_enabled"] = True
                self.setup_shell_integration()
            elif enable_shell_integration == "n":
                config["shell_integration_enabled"] = False

            # Save configuration
            ConfigManager.save_config(config)
            print(Colors.success("Configuration saved."))

        except ConfigError as e:
            print_error(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in setup: {e}", exc_info=True)
            print_error(f"Setup failed: {e}")

    def setup_shell_integration(self) -> None:
        """Set up shell integration for environment-changing commands."""
        print(Colors.highlight("\nShell Integration Setup"))
        print(Colors.highlight("====================="))

        try:
            print(
                Colors.info(
                    "Shell integration allows SmartTerminal to modify your shell environment "
                    "(like changing directories or setting environment variables)."
                )
            )

            # Display instructions
            print(
                Colors.info(
                    "\nTo enable shell integration, you need to add the following to your shell config file:"
                )
            )
            print(self.shell_integration.get_shell_integration_script())

            # Detect shell type
            shell = os.environ.get("SHELL", "")
            if "zsh" in shell:
                config_file = "~/.zshrc"
            elif "bash" in shell:
                config_file = "~/.bashrc"
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
                            f.write(
                                self.shell_integration.get_shell_integration_script()
                            )

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

            # Create a test commands file
            test_commands = [
                "echo 'Shell integration is working!'",
                'cd "$(pwd)"',  # This will just cd to the current directory as a test
            ]

            self.shell_integration.write_shell_commands(
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

        except Exception as e:
            logger.error(
                f"Unexpected error in shell integration setup: {e}", exc_info=True
            )
            print_error(f"Shell integration setup failed: {e}")

    async def run_interactive(self) -> None:
        """Run SmartTerminal in interactive mode."""
        print_banner()
        print(Colors.highlight("SmartTerminal Interactive Mode"))
        print(Colors.info("Type 'exit' or 'quit' to exit"))
        print(Colors.highlight("=============================="))

        # Load chat history
        chat_history = ConfigManager.load_history()

        # Check if shell integration is enabled and remind user
        config = ConfigManager.load_config()
        if (
            config.get("shell_integration_enabled", False)
            and self.shell_integration.check_needs_sourcing()
        ):
            print(
                Colors.info(
                    "\nThere are pending shell changes. To apply them, run: "
                    "source ~/.smartterminal/shell_history/last_commands.sh"
                )
            )

        while True:
            try:
                # Display current directory in prompt
                cwd = os.getcwd()
                username = os.environ.get("USER", os.environ.get("USERNAME", "user"))

                user_input = input(
                    f"\n{Colors.info(f'{username}@{cwd}')} {Colors.cmd('st> ')}"
                )
                if user_input.lower() in ["exit", "quit"]:
                    break

                if not user_input:
                    continue

                # Process the input
                chat_history = await self.process_input(user_input, chat_history)

                # Save updated history
                ConfigManager.save_history(chat_history)

            except KeyboardInterrupt:
                print("\n" + Colors.warning("Exiting..."))
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}", exc_info=True)
                print_error(f"An error occurred: {e}")

    async def run_command(self, command: str) -> None:
        """
        Run a single command through SmartTerminal.

        Args:
            command (str): The natural language command to process.
        """
        # Load chat history
        chat_history = ConfigManager.load_history()

        # Process the command
        chat_history = await self.process_input(command, chat_history)

        # Save updated history
        ConfigManager.save_history(chat_history)
