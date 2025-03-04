"""
Abstract base classes for SmartTerminal core components.

This module defines the abstract interfaces that form the
foundation of SmartTerminal's core functionality.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union

try:
    from smart_terminal.models.config import Config
    from smart_terminal.models.context import ContextData
    from smart_terminal.models.message import Message, UserMessage, AIMessage
    from smart_terminal.models.command import Command, CommandResult, ToolCall

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """
    Abstract interface for AI providers.

    This interface defines the contract that all AI provider
    implementations must fulfill, allowing the application to
    use different AI backends interchangeably.
    """

    @abstractmethod
    async def generate_commands(
        self,
        prompt: str,
        context: Dict[str, Any] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate commands from a natural language prompt.

        Args:
            prompt: Natural language prompt from the user
            context: Optional context information to enhance generation
            system_prompt: Optional system prompt to override default

        Returns:
            List of command dictionaries

        Raises:
            AIError: If command generation fails
        """
        pass

    @abstractmethod
    async def invoke_tool(
        self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Invoke a specific tool with the AI provider.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments
            context: Optional context information

        Returns:
            Tool result dictionary

        Raises:
            AIError: If tool invocation fails
        """
        pass

    @abstractmethod
    def get_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """
        Get the system prompt for command generation.

        Args:
            context: Optional context information

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    def get_command_tool_spec(self) -> Dict[str, Any]:
        """
        Get the command generation tool specification.

        Returns:
            Command tool specification dictionary
        """
        pass


class CommandProcessor(ABC):
    """
    Abstract interface for command processing.

    This interface defines the contract for components that
    process and execute terminal commands.
    """

    @abstractmethod
    def process_commands(self, commands: List[Dict[str, Any]]) -> bool:
        """
        Process and execute a list of commands.

        Args:
            commands: List of command dictionaries

        Returns:
            True if all commands were executed successfully, False otherwise
        """
        pass

    @abstractmethod
    def execute_command(
        self, command: str, requires_admin: bool = False
    ) -> Tuple[bool, str]:
        """
        Execute a shell command and return the result.

        Args:
            command: Command to execute
            requires_admin: Whether the command requires administrator privileges

        Returns:
            Tuple of (success, output/error message)
        """
        pass

    @abstractmethod
    def replace_placeholders(self, command: str, user_inputs: List[str]) -> str:
        """
        Replace placeholders in a command with actual user inputs.

        Args:
            command: Command with placeholders
            user_inputs: List of input parameter names

        Returns:
            Command with placeholders replaced with actual values
        """
        pass


class ShellIntegrator(ABC):
    """
    Abstract interface for shell integration.

    This interface defines the contract for components that
    handle integration with the shell environment.
    """

    @abstractmethod
    def write_shell_commands(self, commands: List[str], description: str = "") -> str:
        """
        Write commands to a file that can be sourced by the parent shell.

        Args:
            commands: List of shell commands to execute
            description: Optional description of what the commands do

        Returns:
            Path to the command file
        """
        pass

    @abstractmethod
    def is_shell_integration_active(self) -> bool:
        """
        Check if shell integration is actively working.

        Returns:
            True if shell integration is working, False otherwise
        """
        pass

    @abstractmethod
    def get_shell_integration_script(self) -> str:
        """
        Get the shell integration script for the user's shell.

        Returns:
            Shell integration script
        """
        pass

    @abstractmethod
    def check_needs_sourcing(self) -> bool:
        """
        Check if there are commands that need to be sourced.

        Returns:
            True if there are commands that need to be sourced
        """
        pass


class ContextProvider(ABC):
    """
    Abstract interface for context generation.

    This interface defines the contract for components that
    generate context information for AI interactions.
    """

    @abstractmethod
    def generate_context(self) -> Dict[str, Any]:
        """
        Generate context information about the current environment.

        Returns:
            Dictionary with context information
        """
        pass

    @abstractmethod
    def get_context_prompt(self) -> str:
        """
        Generate a context prompt for the AI model.

        Returns:
            Formatted context prompt string
        """
        pass

    @abstractmethod
    def update_context(self, command: str, output: str) -> None:
        """
        Update context with a recently executed command.

        Args:
            command: Executed command
            output: Command output
        """
        pass


class TerminalInterface(ABC):
    """
    Abstract interface for the main terminal.

    This interface defines the contract for the main terminal
    component that orchestrates the entire application.
    """

    @abstractmethod
    async def process_input(self, user_query: str) -> Union[bool, Dict[str, Any]]:
        """
        Process user input, generate and execute commands.

        Args:
            user_query: Natural language query from user

        Returns:
            Result of processing (success status or result data)
        """
        pass

    @abstractmethod
    async def run_command(self, command: str) -> Union[bool, Dict[str, Any]]:
        """
        Run a single command through SmartTerminal.

        Args:
            command: Natural language command to process

        Returns:
            Result of command execution
        """
        pass

    @abstractmethod
    async def run_interactive(self) -> None:
        """
        Run SmartTerminal in interactive mode.
        """
        pass

    @abstractmethod
    def setup(self) -> bool:
        """
        Run the setup process to configure SmartTerminal.

        Returns:
            True if setup was successful, False otherwise
        """
        pass

    @abstractmethod
    def set_dry_run(self, enabled: bool) -> None:
        """
        Set dry run mode (show commands without executing them).

        Args:
            enabled: Whether to enable dry run mode
        """
        pass

    @abstractmethod
    def set_json_output(self, enabled: bool) -> None:
        """
        Set JSON output mode.

        Args:
            enabled: Whether to enable JSON output
        """
        pass
