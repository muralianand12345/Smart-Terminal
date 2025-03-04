"""
Command Generation and Execution Module for SmartTerminal.

This module handles generating terminal commands from natural language using AI
and executing those commands with proper user input handling.
"""

import os
import sys
import logging
import subprocess
from typing import List, Dict, Any, Tuple, Optional

from smart_terminal.ai import AIClient, AIError
from smart_terminal.config import ConfigManager

# Setup logging
logger = logging.getLogger("smartterminal.commands")


class CommandError(Exception):
    """Exception raised for command execution errors."""

    pass


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
   - The exact command with specific values where available (don't use placeholders when data is present)
   - List only required user inputs that are actually unknown
   - Specify the OS (default: {default_os})
   - Indicate if admin/root privileges are needed
   - Include a brief description of what this command does

Important rules:
- Generate ONE command per tool call
- If a task requires multiple commands, make multiple separate tool calls in sequence
- Only use placeholders for truly unknown values
- When the user mentions a specific file or directory that was clearly provided, use it directly instead of a placeholder
- For directory navigation, prefer absolute paths with '~' for home directory when appropriate
- Remember the current working directory and reference it for context
- Prefer specific, complete commands over abstract ones with placeholders
- For common directories like 'Desktop', 'Documents', 'Downloads', etc., use them directly without placeholders
- Default to {default_os} commands unless specified otherwise
- For 'cd' commands, always use the full directory path if known from context
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

        except AIError:
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
        command_str: str, requires_admin: bool = False, shell_integration: bool = False
    ) -> Tuple[bool, str]:
        """
        Execute a shell command and return the output.

        Args:
            command_str (str): Command to execute.
            requires_admin (bool): Whether the command requires admin privileges.
            shell_integration (bool): Whether to use shell integration for environment-changing commands.

        Returns:
            Tuple[bool, str]: Success status and output/error message.

        Raises:
            CommandError: If the command execution fails.
        """
        try:
            logger.debug(
                f"Executing command: {command_str}, requires_admin={requires_admin}"
            )

            # Handle cd commands using shell integration
            if command_str.strip().startswith("cd ") and shell_integration:
                from smart_terminal.shell_integration import ShellIntegration

                shell = ShellIntegration()

                # Extract the target directory
                target_dir = command_str.strip()[3:].strip()

                # Write the command to a file that will be sourced by the shell
                shell.write_shell_commands([command_str], "Change directory")

                # For preview, attempt to change directory and show result
                # This won't affect the parent shell but gives feedback
                if target_dir.startswith("~"):
                    target_dir = os.path.expanduser(target_dir)

                try:
                    os.chdir(target_dir)
                    return (
                        True,
                        f"Shell integration: Directory will be changed to: {os.getcwd()}\n(Note: You'll need to source the command file or use the shell integration to apply this change)",
                    )
                except FileNotFoundError:
                    return False, f"Directory not found: {target_dir}"
                except PermissionError:
                    return False, f"Permission denied: {target_dir}"
                except Exception as e:
                    return False, str(e)

            # Handle environment variable setting with shell integration
            if (
                command_str.strip().startswith("export ")
                or "=" in command_str.strip().split()[0]
            ) and shell_integration:
                from smart_terminal.shell_integration import ShellIntegration

                shell = ShellIntegration()

                # Write the command to a file that will be sourced by the shell
                shell.write_shell_commands([command_str], "Set environment variable")

                return (
                    True,
                    "Shell integration: Environment variable will be set\n(Note: You'll need to source the command file or use the shell integration to apply this change)",
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

        from smart_terminal.utils import Colors

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

    @classmethod
    def process_commands(cls, commands: List[Dict[str, Any]]) -> None:
        """
        Process and execute a list of commands.

        Args:
            commands (List[Dict[str, Any]]): List of command data dictionaries.

        Returns:
            bool: True if all commands were executed successfully, False otherwise.
        """
        from smart_terminal.utils import Colors
        from smart_terminal.config import ConfigManager

        # Check if shell integration is enabled in config
        config = ConfigManager.load_config()
        shell_integration_enabled = config.get("shell_integration_enabled", False)

        environment_changing_commands = ["cd ", "export ", "="]
        commands_for_shell_integration = []
        success = True

        # Process each command
        for i, cmd in enumerate(commands):
            command = cmd.get("command", "")
            user_inputs = cmd.get("user_inputs", [])
            requires_admin = cmd.get("requires_admin", False) or "sudo" in user_inputs
            description = cmd.get("description", "")
            os_type = cmd.get("os", "")

            print(f"\n{Colors.highlight(f'Command {i + 1}:')} {Colors.cmd(command)}")
            print(f"{Colors.highlight('Description:')} {description}")

            if os_type:
                print(f"{Colors.highlight('OS:')} {os_type}")

            # Check if user wants to execute this command
            confirmation = input(
                Colors.warning("Execute this command? (y/n): ")
            ).lower()
            if confirmation != "y":
                print(Colors.info("Command skipped."))
                continue

            # Replace placeholders and execute
            final_command = cls.replace_placeholders(command, user_inputs)
            print(Colors.info(f"Executing: {Colors.cmd(final_command)}"))

            try:
                # Check if this is an environment-changing command that needs shell integration
                needs_shell_integration = shell_integration_enabled and any(
                    final_command.strip().startswith(prefix)
                    for prefix in environment_changing_commands
                )

                if needs_shell_integration:
                    commands_for_shell_integration.append(final_command)

                success_cmd, output = cls.execute_command(
                    final_command,
                    requires_admin,
                    shell_integration=needs_shell_integration,
                )
                success = success and success_cmd

                if success_cmd:
                    print(Colors.success("Command executed successfully:"))
                    if output.strip():  # Only print output if it's not empty
                        print(output)

                    # Show current directory after execution (especially for cd commands)
                    current_dir = os.getcwd()
                    username = os.environ.get(
                        "USER", os.environ.get("USERNAME", "user")
                    )
                    hostname = os.environ.get(
                        "HOSTNAME", os.environ.get("COMPUTERNAME", "localhost")
                    )
                    print(f"\n{Colors.info(f'{username}@{hostname} {current_dir} % ')}")
                else:
                    print(Colors.error("Command failed:"))
                    print(output)
            except CommandError as e:
                success = False
                from smart_terminal.utils import print_error

                print_error(str(e))

        # Only write shell integration commands if there are environment-changing commands
        # that require shell integration
        if commands_for_shell_integration and shell_integration_enabled:
            from smart_terminal.shell_integration import ShellIntegration

            shell = ShellIntegration()

            # Create the shell commands file with the commands
            shell.write_shell_commands(
                commands_for_shell_integration, "Generated by SmartTerminal"
            )

            # Now check if shell integration is active
            shell_integration_working = shell.is_shell_integration_active()

            # Only show the reminder if shell integration is not working
            if not shell_integration_working and shell.check_needs_sourcing():
                print(f"\n{Colors.highlight('Shell Integration:')}")
                print(
                    Colors.info(
                        "To apply environment changes, run: source ~/.smartterminal/shell_history/last_commands.sh"
                    )
                )

        return success
