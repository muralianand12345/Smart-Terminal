#!/usr/bin/env python3
"""
SmartTerminal: AI-Powered Terminal Command Generator and Executor

This module provides a CLI tool that converts natural language instructions into
executable terminal commands. It uses AI to generate appropriate commands with
placeholders for user input.

Features:
- Convert natural language to terminal commands
- Handle multi-step tasks with sequential commands
- Collect user input for command parameters
- Support for different operating systems
- Interactive mode for continuous command generation
- Command history for context-aware interactions
- Proper handling of administrative privileges

Author: Murali Anand (https://github.com/muralianand12345)
Version: 1.0.1
"""

import sys
import json
import asyncio
import argparse
import subprocess
import logging
from pathlib import Path
import readline  # For command history
from typing import List, Iterable, Any, Optional, Dict, Tuple


# Terminal colors for better UX
class Colors:
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
        return f"{cls.RED}{text}{cls.RESET}"

    @classmethod
    def success(cls, text: str) -> str:
        return f"{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def warning(cls, text: str) -> str:
        return f"{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def info(cls, text: str) -> str:
        return f"{cls.BLUE}{text}{cls.RESET}"

    @classmethod
    def cmd(cls, text: str) -> str:
        return f"{cls.CYAN}{text}{cls.RESET}"

    @classmethod
    def highlight(cls, text: str) -> str:
        return f"{cls.BOLD}{text}{cls.RESET}"


# Setup logging
logger = logging.getLogger("smartterminal")


def setup_logging(level_name: str = "INFO") -> None:
    """Configure logging based on the specified level."""
    level = getattr(logging, level_name.upper(), logging.INFO)

    # Clear existing handlers
    logger.handlers = []

    # Set level
    logger.setLevel(level)

    if level == logging.DEBUG:
        # Debug format with timestamp
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
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


# Try import required packages
try:
    from openai import AsyncOpenAI, OpenAI
    from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
    from openai.types.chat.chat_completion_message_param import (
        ChatCompletionMessageParam,
    )
    from pydantic import BaseModel, Field, ConfigDict
except ImportError as e:
    print_error(
        "Required packages not found. Please install 'openai' and 'pydantic' using 'pip install openai pydantic'"
    )
    logger.error(f"Import error: {e}")
    sys.exit(1)


class ConfigError(Exception):
    """Exception raised for configuration errors."""

    pass


class CommandError(Exception):
    """Exception raised for command execution errors."""

    pass


class AIError(Exception):
    """Exception raised for AI interaction errors."""

    pass


class ConfigManager:
    """
    Manages configuration settings for SmartTerminal.

    This class handles loading, saving, and updating configuration settings,
    and provides default values when settings are not available.
    """

    # Configuration paths
    CONFIG_DIR = Path.home() / ".smartterminal"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    HISTORY_FILE = CONFIG_DIR / "history.json"

    # Default configuration settings
    DEFAULT_CONFIG = {
        "api_key": "",
        "base_url": "https://api.groq.com/openai/v1",
        "model_name": "llama-3.3-70b-versatile",
        "default_os": "macos",
        "history_limit": 20,
        "log_level": "INFO",
    }

    @classmethod
    def init_config(cls) -> None:
        """
        Initialize configuration directories and files.

        Creates the configuration directory and files if they don't exist.
        If the config file doesn't exist, it creates it with default settings
        and exits with a message to set the API key.

        Raises:
            ConfigError: If there's an error creating configuration files.
        """
        try:
            cls.CONFIG_DIR.mkdir(exist_ok=True)

            # Create config file if it doesn't exist
            if not cls.CONFIG_FILE.exists():
                with open(cls.CONFIG_FILE, "w") as f:
                    json.dump(cls.DEFAULT_CONFIG, f, indent=2)
                print(
                    Colors.warning(
                        f"Created default config at {cls.CONFIG_FILE}. Please set your API key."
                    )
                )
                sys.exit(1)

            # Create history file if it doesn't exist
            if not cls.HISTORY_FILE.exists():
                with open(cls.HISTORY_FILE, "w") as f:
                    json.dump([], f)
        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            raise ConfigError(f"Failed to initialize configuration: {e}")

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Dict[str, Any]: Configuration settings as a dictionary.

        Raises:
            ConfigError: If there's an error loading the configuration.
        """
        try:
            with open(cls.CONFIG_FILE, "r") as f:
                config = json.load(f)

            return config
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Error loading config, using defaults: {e}")
            return cls.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}")
            raise ConfigError(f"Failed to load configuration: {e}")

    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> None:
        """
        Save configuration to file.

        Args:
            config (Dict[str, Any]): Configuration settings to save.

        Raises:
            ConfigError: If there's an error saving the configuration.
        """
        try:
            with open(cls.CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigError(f"Failed to save configuration: {e}")

    @classmethod
    def load_history(cls) -> List[Dict[str, Any]]:
        """
        Load chat history from file.

        Returns:
            List[Dict[str, Any]]: Chat history as a list of message objects.
        """
        try:
            with open(cls.HISTORY_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.debug("History file not found or invalid, returning empty history")
            return []
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    @classmethod
    def save_history(cls, history: List[Dict[str, Any]]) -> None:
        """
        Save chat history to file, limited to configured size.

        Args:
            history (List[Dict[str, Any]]): Chat history to save.
        """
        try:
            config = cls.load_config()
            # Limit history to configured size
            if len(history) > config["history_limit"]:
                history = history[-config["history_limit"] :]

            with open(cls.HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            print_error(f"Could not save command history: {e}")


class Message(BaseModel):
    """Message model for chat interactions."""

    role: str = Field(..., description="The role of the message")
    content: str = Field(..., description="The content of the message")
    model_config = ConfigDict(protected_namespaces=())


class Tools(BaseModel):
    """Tools model for AI function calls."""

    tools: List[str] = Field(..., description="The tools to use")
    model_config = ConfigDict(protected_namespaces=())


class AIClient:
    """
    Base class for AI API interactions.

    This class provides methods for making API calls to AI providers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize AI client with API credentials and settings.

        Args:
            api_key (Optional[str]): API key for authentication.
            base_url (Optional[str]): Base URL for API calls.
            model_name (Optional[str]): AI model name to use.
        """
        self.base_url = base_url or "https://api.groq.com/openai/v1"
        self.model_name = model_name or "llama-3.3-70b-versatile"
        self.api_key = api_key

        # Initialize clients
        try:
            self.sync_client = OpenAI(api_key=api_key, base_url=self.base_url)
            self.async_client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
            raise AIError(f"Failed to initialize AI client: {e}")

    @staticmethod
    def create_tool_spec(
        name: str, description: str, parameters: dict, **kwargs
    ) -> Dict[str, Any]:
        """
        Create a tool specification for function calling.

        Args:
            name (str): Tool name.
            description (str): Tool description.
            parameters (dict): JSON schema for parameters.
            **kwargs: Additional tool properties.

        Returns:
            Dict[str, Any]: Tool specification.
        """
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
                "strict": True,
                **kwargs,
            },
        }

    async def invoke_tool_async(
        self,
        tools: Iterable[ChatCompletionToolParam],
        messages: Iterable[ChatCompletionMessageParam],
        **kwargs,
    ) -> Any:
        """
        Invoke tool asynchronously via AI API.

        Args:
            tools: Tool specifications.
            messages: Chat messages.
            **kwargs: Additional API parameters.

        Returns:
            Tool call objects from the API response.

        Raises:
            AIError: If the API call fails.
        """
        try:
            logger.debug(f"Invoking AI with {len(messages)} messages")
            tools_response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                temperature=0.0,
                tool_choice="auto",
                **kwargs,
            )

            return tools_response.choices[0].message.tool_calls

        except Exception as e:
            logger.error(f"AI tool invocation failed: {e}")
            raise AIError(f"Error communicating with AI service: {e}")

    def invoke_tool_sync(
        self,
        tools: Iterable[ChatCompletionToolParam],
        messages: Iterable[ChatCompletionMessageParam],
        **kwargs,
    ) -> Any:
        """
        Invoke tool synchronously via AI API.

        Args:
            tools: Tool specifications.
            messages: Chat messages.
            **kwargs: Additional API parameters.

        Returns:
            Tool call objects from the API response.

        Raises:
            AIError: If the API call fails.
        """
        try:
            logger.debug(f"Invoking AI synchronously with {len(messages)} messages")
            tools_response = self.sync_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                temperature=0.0,
                tool_choice="auto",
                **kwargs,
            )

            return tools_response.choices[0].message.tool_calls

        except Exception as e:
            logger.error(f"Synchronous AI tool invocation failed: {e}")
            raise AIError(f"Error communicating with AI service: {e}")


class CommandGenerator:
    """
    Generates terminal commands from natural language using AI.

    This class handles the interaction with the AI to convert
    natural language requests into executable terminal commands.
    """

    def __init__(self, ai_client: AIClient):
        """
        Initialize command generator with AI client.

        Args:
            ai_client (AIClient): AI client for API calls.
        """
        self.ai_client = ai_client

    @staticmethod
    def create_command_tool() -> Dict[str, Any]:
        """
        Create the command generation tool specification.

        Returns:
            Dict[str, Any]: Tool specification for command generation.
        """
        return {
            "type": "function",
            "function": {
                "name": "get_command",
                "description": "Get a single terminal command to execute. For tasks requiring multiple commands, this tool should be called multiple times in sequence.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "A single terminal command with placeholders for user inputs enclosed in angle brackets (e.g., 'mkdir <folder_name>')",
                        },
                        "user_inputs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of input values that the user needs to provide to execute the command. These correspond to the placeholders in the command string.",
                        },
                        "os": {
                            "type": "string",
                            "enum": ["macos", "linux", "windows"],
                            "description": "The operating system for which this command is intended",
                            "default": "macos",
                        },
                        "requires_admin": {
                            "type": "boolean",
                            "description": "Whether this command requires administrator or root privileges",
                            "default": False,
                        },
                        "description": {
                            "type": "string",
                            "description": "A brief description of what this command does",
                        },
                    },
                    "required": ["command", "user_inputs"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }

    @staticmethod
    def get_system_prompt(default_os: str = "macos") -> str:
        """
        Get the system prompt for the AI model.

        Args:
            default_os (str): Default operating system to use for commands.

        Returns:
            str: System prompt instructing the AI how to generate commands.
        """
        return f"""You are an expert terminal command assistant. 
        
When users request tasks:
1. Break complex tasks into individual terminal commands
2. For each command, specify:
   - The exact command with placeholders (like <folder_name>) for user inputs
   - List all required user inputs that correspond to placeholders
   - Specify the OS (default: {default_os})
   - Indicate if admin/root privileges are needed
   - Include a brief description of what this command does

Important rules:
- Generate ONE command per tool call
- If a task requires multiple commands, make multiple separate tool calls in sequence
- Use placeholders with angle brackets for any user input values
- Make sure the user_inputs field contains strings matching EXACTLY to the placeholders in the command (without the < >)
- Include "sudo" in user_inputs list if the command requires admin privileges
- Make commands as specific and accurate as possible
- Default to {default_os} commands unless specified otherwise
"""

    async def generate_commands(
        self, user_query: str, chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Any]:
        """
        Generate a sequence of commands from a natural language query.

        Args:
            user_query (str): Natural language query from user.
            chat_history (Optional[List[Dict[str, Any]]]): Previous chat history for context.

        Returns:
            List[Any]: List of command sets generated by the AI.

        Raises:
            AIError: If command generation fails.
        """
        # Create our enhanced tool
        command_tool = self.create_command_tool()
        tools = [command_tool]

        # Get default OS from config
        config = ConfigManager.load_config()
        default_os = config.get("default_os", "macos")

        # System message
        system_message = {
            "role": "system",
            "content": self.get_system_prompt(default_os),
        }

        # Initialize messages with history if provided
        if chat_history and len(chat_history) > 0:
            messages = (
                [system_message]
                + chat_history
                + [{"role": "user", "content": user_query}]
            )
        else:
            messages = [system_message, {"role": "user", "content": user_query}]

        try:
            logger.debug(f"Generating commands for query: {user_query}")

            # Get the first command
            response = await self.ai_client.invoke_tool_async(
                tools=tools, messages=messages
            )

            if not response:
                logger.debug("No commands generated")
                return []

            # Store the initial response
            all_commands = [response]

            # Continue the conversation to get any additional commands needed
            updated_messages = messages.copy()

            # Add the assistant's response with the first tool call
            updated_messages.append(
                {"role": "assistant", "content": None, "tool_calls": response}
            )

            # Add feedback that we need any subsequent commands
            updated_messages.append(
                {
                    "role": "user",
                    "content": "What other commands are needed to complete this task? If no more commands are needed, please respond with 'No more commands needed.'",
                }
            )

            # Keep getting additional commands until the model indicates it's done
            max_iterations = 5  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"Getting additional commands (iteration {iteration})")

                next_response = await self.ai_client.invoke_tool_async(
                    tools=tools, messages=updated_messages
                )

                # Check if we're done (no more tool calls or empty response)
                if not next_response:
                    logger.debug("No more commands needed")
                    break

                # Add this command to our list
                all_commands.append(next_response)

                # Update messages for the next iteration
                updated_messages.append(
                    {"role": "assistant", "content": None, "tool_calls": next_response}
                )

                updated_messages.append(
                    {
                        "role": "user",
                        "content": "Are there any more commands needed? If not, please respond with 'No more commands needed.'",
                    }
                )

            logger.debug(f"Generated {len(all_commands)} command sets")
            return all_commands

        except AIError as e:
            # Re-raise AIError since it's already properly formatted
            raise
        except Exception as e:
            logger.error(f"Unexpected error in command generation: {e}")
            raise AIError(f"Failed to generate commands: {e}")


class CommandExecutor:
    """
    Executes terminal commands with proper user input handling.

    This class handles executing generated commands, including
    placeholder replacement and sudo handling.
    """

    @staticmethod
    def execute_command(
        command_str: str, requires_admin: bool = False
    ) -> Tuple[bool, str]:
        """
        Execute a shell command and return the output.

        Args:
            command_str (str): Command to execute.
            requires_admin (bool): Whether the command requires admin privileges.

        Returns:
            Tuple[bool, str]: Success status and output/error message.

        Raises:
            CommandError: If the command execution fails.
        """
        try:
            logger.debug(
                f"Executing command: {command_str}, requires_admin={requires_admin}"
            )

            if requires_admin and sys.platform != "win32":
                command_str = f"sudo {command_str}"

            result = subprocess.run(
                command_str, shell=True, capture_output=True, text=True
            )

            if result.returncode == 0:
                logger.debug("Command executed successfully")
                return True, result.stdout
            else:
                logger.error(
                    f"Command failed with return code {result.returncode}: {result.stderr}"
                )
                return False, result.stderr
        except Exception as e:
            logger.error(f"Exception while executing command: {e}")
            raise CommandError(f"Command execution failed: {e}")

    @staticmethod
    def prompt_for_input(input_name: str) -> str:
        """
        Prompt the user for input for a command parameter.

        Args:
            input_name (str): Name of the parameter.

        Returns:
            str: User-provided value.
        """
        if input_name.lower() == "sudo":
            return "sudo"  # Just return the sudo command itself

        value = input(f"Enter value for {Colors.highlight(input_name)}: ")
        return value

    @classmethod
    def replace_placeholders(cls, command: str, user_inputs: List[str]) -> str:
        """
        Replace placeholders in a command with actual user inputs.

        Args:
            command (str): Command with placeholders.
            user_inputs (List[str]): List of input parameter names.

        Returns:
            str: Command with placeholders replaced with actual values.
        """
        logger.debug(f"Replacing placeholders in command: {command}")
        logger.debug(f"User inputs: {user_inputs}")

        # Create a copy of the original command
        final_command = command

        # Replace placeholders that match user_inputs
        for input_name in user_inputs:
            if input_name.lower() == "sudo":
                # Skip sudo as we handle it separately
                continue

            value = cls.prompt_for_input(input_name)
            placeholder = f"<{input_name}>"

            # Replace the placeholder with the actual value
            final_command = final_command.replace(placeholder, value)
            logger.debug(f"Replaced '{placeholder}' with '{value}'")

        # Check for any remaining placeholders
        while "<" in final_command and ">" in final_command:
            start_idx = final_command.find("<")
            end_idx = final_command.find(">", start_idx)

            if start_idx != -1 and end_idx != -1:
                placeholder = final_command[start_idx : end_idx + 1]
                placeholder_name = placeholder[1:-1]  # Remove < and >
                logger.debug(f"Found additional placeholder: {placeholder}")

                # Ask for value for this placeholder
                value = cls.prompt_for_input(placeholder_name)

                # Replace the placeholder
                final_command = final_command.replace(placeholder, value)
                logger.debug(f"Replaced '{placeholder}' with '{value}'")
            else:
                # No more valid placeholders found, break the loop
                break

        logger.debug(f"Final command after replacement: {final_command}")
        return final_command


class SmartTerminal:
    """
    Main class for the SmartTerminal application.

    This class orchestrates the command generation and execution process,
    manages user interaction, and maintains conversation history.
    """

    def __init__(self):
        """Initialize SmartTerminal with configuration and components."""
        try:
            # Initialize configuration
            ConfigManager.init_config()
            config = ConfigManager.load_config()

            # Setup logging based on configuration
            log_level = config.get("log_level", "INFO")
            setup_logging(log_level)

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

            # Execute each command
            for i, cmd in enumerate(commands):
                command = cmd.get("command", "")
                user_inputs = cmd.get("user_inputs", [])
                requires_admin = (
                    cmd.get("requires_admin", False) or "sudo" in user_inputs
                )
                description = cmd.get("description", "")

                print(
                    f"\n{Colors.highlight(f'Command {i + 1}:')} {Colors.cmd(command)}"
                )
                print(f"{Colors.highlight('Description:')} {description}")

                # Check if user wants to execute this command
                confirmation = input(
                    Colors.warning("Execute this command? (y/n): ")
                ).lower()
                if confirmation != "y":
                    print(Colors.info("Command skipped."))
                    continue

                # Replace placeholders and execute
                final_command = CommandExecutor.replace_placeholders(
                    command, user_inputs
                )
                print(Colors.info(f"Executing: {Colors.cmd(final_command)}"))

                try:
                    success, output = CommandExecutor.execute_command(
                        final_command, requires_admin
                    )

                    if success:
                        print(Colors.success("Command executed successfully:"))
                        print(output)
                    else:
                        print(Colors.error("Command failed:"))
                        print(output)
                except CommandError as e:
                    print_error(str(e))

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


def main() -> None:
    """Main entry point for the SmartTerminal CLI."""
    try:
        # Parse arguments
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

        args = parser.parse_args()

        # Show version
        if args.version:
            print(Colors.highlight("SmartTerminal v1.0.1"))
            return

        # Initialize basic logging
        log_level = "DEBUG" if args.debug else "INFO"
        setup_logging(log_level)

        # Initialize SmartTerminal
        terminal = SmartTerminal()

        # Setup command
        if args.setup:
            terminal.setup()
            return

        # Clear history
        if args.clear_history:
            ConfigManager.save_history([])
            print(Colors.success("Command history cleared."))
            return

        # Check if API key is set
        config = ConfigManager.load_config()
        if not config.get("api_key"):
            print(
                Colors.warning("API key not set. Please run 'st --setup' to configure.")
            )
            return

        # Interactive mode
        if args.interactive:
            asyncio.run(terminal.run_interactive())
            return

        # Process a single command
        if args.command:
            asyncio.run(terminal.run_command(args.command))
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n" + Colors.warning("Operation cancelled by user."))
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        print_error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
