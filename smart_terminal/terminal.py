"""
Main SmartTerminal class implementation.

This module provides the core SmartTerminal class that orchestrates
the command generation and execution process, manages user interaction,
and maintains conversation history.
"""

import json
import logging
from typing import List, Dict, Any, Optional

from smart_terminal.ai import AIClient, AIError
from smart_terminal.commands import CommandGenerator, CommandExecutor
from smart_terminal.config import ConfigManager, ConfigError
from smart_terminal.utils import Colors, print_error, print_banner

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

        # Initialize or use provided chat history
        if chat_history is None:
            chat_history = []

        # Add user query to history
        chat_history.append({"role": "user", "content": user_query})

        try:
            # Get commands
            command_sets = await self.command_generator.generate_commands(
                user_query, chat_history
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

            # Process and execute commands
            CommandExecutor.process_commands(commands)

            # Update chat history with executed commands
            assistant_content = "I executed the following commands:\n"
            for cmd in commands:
                assistant_content += f"- {cmd.get('command', '')}\n"

            chat_history.append({"role": "assistant", "content": assistant_content})

            # Trim history if needed
            config = ConfigManager.load_config()
            history_limit = config.get("history_limit", 20)
            if len(chat_history) > history_limit:
                chat_history = chat_history[-history_limit:]

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

            # Save configuration
            ConfigManager.save_config(config)
            print(Colors.success("Configuration saved."))

        except ConfigError as e:
            print_error(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in setup: {e}", exc_info=True)
            print_error(f"Setup failed: {e}")

    async def run_interactive(self) -> None:
        """Run SmartTerminal in interactive mode."""
        print_banner()
        print(Colors.highlight("SmartTerminal Interactive Mode"))
        print(Colors.info("Type 'exit' or 'quit' to exit"))
        print(Colors.highlight("=============================="))

        # Load chat history
        chat_history = ConfigManager.load_history()

        while True:
            try:
                user_input = input(f"\n{Colors.cmd('st> ')}")
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
