"""
Tests for the commands module.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from smart_terminal.commands import CommandGenerator, CommandExecutor, CommandError
from smart_terminal.ai import AIError


class TestCommandGenerator:
    """Tests for the CommandGenerator class."""

    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client."""
        mock_client = MagicMock()
        mock_client.invoke_tool_async = AsyncMock()
        return mock_client

    def test_init(self, mock_ai_client):
        """Test initializing the CommandGenerator."""
        generator = CommandGenerator(mock_ai_client)
        assert generator.ai_client == mock_ai_client

    def test_create_command_tool(self):
        """Test creating the command generation tool spec."""
        tool_spec = CommandGenerator.create_command_tool()

        assert tool_spec["type"] == "function"
        assert tool_spec["function"]["name"] == "get_command"
        assert "description" in tool_spec["function"]
        assert "parameters" in tool_spec["function"]

        # Check required parameters
        required_params = tool_spec["function"]["parameters"]["required"]
        assert "command" in required_params
        assert "user_inputs" in required_params

    def test_get_system_prompt(self):
        """Test generating the system prompt."""
        # Test with default OS
        prompt = CommandGenerator.get_system_prompt()
        assert "You are an expert terminal command assistant" in prompt
        assert "Default to macos commands" in prompt

        # Test with specific OS
        prompt = CommandGenerator.get_system_prompt("linux")
        assert "Default to linux commands" in prompt

    @pytest.mark.asyncio
    async def test_generate_commands_success(self, mock_ai_client):
        """Test successfully generating commands."""
        # Setup mock response
        tool_call_1 = MagicMock()
        tool_call_1.function.arguments = json.dumps(
            {
                "command": "ls -la",
                "user_inputs": [],
                "os": "macos",
                "requires_admin": False,
                "description": "List all files in the current directory",
            }
        )

        # Set up the mock to return different values on subsequent calls
        # First call returns one command, subsequent calls return empty (no more commands)
        mock_ai_client.invoke_tool_async.side_effect = [
            [tool_call_1],  # First call returns the command
            [],  # Second call returns empty (no more commands)
        ]

        # Create generator and test
        generator = CommandGenerator(mock_ai_client)
        commands = await generator.generate_commands("list all files")

        # Check that the AI client was called with the correct parameters
        assert mock_ai_client.invoke_tool_async.called
        call_args = mock_ai_client.invoke_tool_async.call_args_list[0][1]
        assert len(call_args["tools"]) == 1
        assert call_args["tools"][0]["function"]["name"] == "get_command"

        # With our mock setup, we should get exactly one command array back
        assert len(commands) == 1
        assert commands[0] == [tool_call_1]

    @pytest.mark.asyncio
    async def test_generate_commands_multiple_iterations(self, mock_ai_client):
        """Test generating multiple commands with iterations."""
        # Setup initial response
        tool_call_1 = MagicMock()
        tool_call_1.function.arguments = json.dumps(
            {
                "command": "mkdir testdir",
                "user_inputs": [],
                "os": "macos",
                "description": "Create a directory",
            }
        )

        # Setup second response
        tool_call_2 = MagicMock()
        tool_call_2.function.arguments = json.dumps(
            {
                "command": "cd testdir",
                "user_inputs": [],
                "os": "macos",
                "description": "Change to the new directory",
            }
        )

        # Setup third response (empty to end the loop)
        mock_ai_client.invoke_tool_async.side_effect = [
            [tool_call_1],  # First call returns first command
            [tool_call_2],  # Second call returns second command
            [],  # Third call returns empty list (no more commands)
        ]

        # Create generator and test
        generator = CommandGenerator(mock_ai_client)
        commands = await generator.generate_commands("create a dir and enter it")

        # Check the calls and results
        assert mock_ai_client.invoke_tool_async.call_count == 3
        assert len(commands) == 2
        assert commands[0] == [tool_call_1]
        assert commands[1] == [tool_call_2]

    @pytest.mark.asyncio
    async def test_generate_commands_no_commands(self, mock_ai_client):
        """Test handling when no commands are generated."""
        mock_ai_client.invoke_tool_async.return_value = []

        generator = CommandGenerator(mock_ai_client)
        commands = await generator.generate_commands("invalid request")

        assert commands == []
        assert mock_ai_client.invoke_tool_async.called

    @pytest.mark.asyncio
    async def test_generate_commands_with_history(self, mock_ai_client):
        """Test generating commands with chat history."""
        # Setup mock response
        tool_call = MagicMock()
        tool_call.function.arguments = json.dumps(
            {
                "command": "echo hello",
                "user_inputs": [],
                "os": "macos",
                "description": "Echo hello",
            }
        )

        # Set up the mock to return different values on subsequent calls
        mock_ai_client.invoke_tool_async.side_effect = [
            [tool_call],  # First call returns one command
            [],  # Second call returns empty (no more commands)
        ]

        # Create chat history
        chat_history = [
            {"role": "user", "content": "previous command"},
            {"role": "assistant", "content": "response"},
        ]

        # Create generator and test
        generator = CommandGenerator(mock_ai_client)
        commands = await generator.generate_commands("echo hello", chat_history)

        # Check that the AI client was called with the history
        call_args = mock_ai_client.invoke_tool_async.call_args_list[0][1]
        messages = call_args["messages"]

        # The first message should be the system prompt, followed by the history, then the new message
        assert len(messages) == 4  # system + 2 history + 1 new
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "previous command"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "response"
        assert messages[3]["role"] == "user"
        assert "echo hello" in messages[3]["content"]

        # Check the returned commands - should have 1 command
        assert len(commands) == 1

    @pytest.mark.asyncio
    async def test_generate_commands_ai_error(self, mock_ai_client):
        """Test handling AI errors during command generation."""
        mock_ai_client.invoke_tool_async.side_effect = AIError("API error")

        generator = CommandGenerator(mock_ai_client)

        # The method should re-raise AIError
        with pytest.raises(AIError):
            await generator.generate_commands("test command")

    @pytest.mark.asyncio
    async def test_generate_commands_other_error(self, mock_ai_client):
        """Test handling other errors during command generation."""
        mock_ai_client.invoke_tool_async.side_effect = Exception("Unexpected error")

        generator = CommandGenerator(mock_ai_client)

        # Should wrap the error in AIError
        with pytest.raises(AIError) as excinfo:
            await generator.generate_commands("test command")

        assert "Failed to generate commands" in str(excinfo.value)


class TestCommandExecutor:
    """Tests for the CommandExecutor class."""

    def test_execute_command_success(self):
        """Test successful command execution."""
        with patch("subprocess.run") as mock_run:
            # Setup mock subprocess response
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "Command output"
            mock_run.return_value = mock_process

            # Execute command
            success, output = CommandExecutor.execute_command("echo test")

            # Check the result
            assert success is True
            assert output == "Command output"
            mock_run.assert_called_once_with(
                "echo test", shell=True, capture_output=True, text=True
            )

    def test_execute_command_failure(self):
        """Test command execution failure."""
        with patch("subprocess.run") as mock_run:
            # Setup mock subprocess response
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.stderr = "Command error"
            mock_run.return_value = mock_process

            # Execute command
            success, output = CommandExecutor.execute_command("invalid command")

            # Check the result
            assert success is False
            assert output == "Command error"

    def test_execute_command_exception(self):
        """Test exception handling during command execution."""
        with patch("subprocess.run", side_effect=Exception("Execution error")):
            # The method should raise CommandError
            with pytest.raises(CommandError) as excinfo:
                CommandExecutor.execute_command("echo test")

            assert "Command execution failed" in str(excinfo.value)

    def test_execute_command_with_admin(self):
        """Test command execution with admin privileges."""
        with (
            patch("subprocess.run") as mock_run,
            patch("sys.platform", "darwin"),
        ):  # macOS platform
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            # Execute command with admin privileges
            CommandExecutor.execute_command("apt update", requires_admin=True)

            # Check that sudo was added to the command
            mock_run.assert_called_once_with(
                "sudo apt update", shell=True, capture_output=True, text=True
            )

    def test_cd_command_with_shell_integration(self):
        """Test handling cd commands with shell integration."""
        with (
            patch("os.chdir") as mock_chdir,
            patch("smart_terminal.shell_integration.ShellIntegration") as mock_shell,
        ):
            # Setup mock shell integration
            shell_instance = MagicMock()
            mock_shell.return_value = shell_instance

            # Test the cd command
            success, output = CommandExecutor.execute_command(
                "cd /tmp", requires_admin=False, shell_integration=True
            )

            # Check that shell integration was used
            assert shell_instance.write_shell_commands.called
            mock_chdir.assert_called_once_with("/tmp")
            assert success is True
            assert "Shell integration" in output

    def test_replace_placeholders(self):
        """Test replacing placeholders in commands."""
        with patch(
            "smart_terminal.commands.CommandExecutor.prompt_for_input"
        ) as mock_prompt:
            mock_prompt.side_effect = ["value1", "value2"]

            command = "mkdir <dir_name> && cd <dir_name>"
            user_inputs = ["dir_name"]

            result = CommandExecutor.replace_placeholders(command, user_inputs)

            assert result == "mkdir value1 && cd value1"
            assert mock_prompt.call_count == 1

    def test_replace_placeholders_additional(self):
        """Test replacing additional placeholders not in user_inputs."""
        with patch(
            "smart_terminal.commands.CommandExecutor.prompt_for_input"
        ) as mock_prompt:
            mock_prompt.side_effect = ["value1", "value2"]

            command = "mkdir <dir_name> && touch <dir_name>/<file_name>"
            user_inputs = ["dir_name"]

            result = CommandExecutor.replace_placeholders(command, user_inputs)

            assert result == "mkdir value1 && touch value1/value2"
            assert mock_prompt.call_count == 2

    def test_prompt_for_input(self):
        """Test prompting for input."""
        with patch("builtins.input", return_value="test_value"):
            value = CommandExecutor.prompt_for_input("parameter_name")
            assert value == "test_value"

    def test_prompt_for_sudo(self):
        """Test handling the special sudo input."""
        value = CommandExecutor.prompt_for_input("sudo")
        assert value == "sudo"

    def test_process_commands(self):
        """Test processing and executing a list of commands."""
        with (
            patch(
                "smart_terminal.commands.CommandExecutor.replace_placeholders"
            ) as mock_replace,
            patch(
                "smart_terminal.commands.CommandExecutor.execute_command"
            ) as mock_execute,
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):
            mock_replace.return_value = "ls -la"
            mock_execute.return_value = (True, "command output")

            commands = [
                {
                    "command": "ls -la <dir>",
                    "user_inputs": ["dir"],
                    "requires_admin": False,
                    "description": "List directory contents",
                }
            ]

            # Process commands
            CommandExecutor.process_commands(commands)

            # Check that replace_placeholders and execute_command were called
            mock_replace.assert_called_once_with("ls -la <dir>", ["dir"])
            mock_execute.assert_called_once_with(
                "ls -la", False, shell_integration=False
            )

    def test_process_commands_skip(self):
        """Test skipping commands when user declines execution."""
        with (
            patch(
                "smart_terminal.commands.CommandExecutor.execute_command"
            ) as mock_execute,
            patch("builtins.input", return_value="n"),
            patch("builtins.print"),
        ):
            commands = [
                {
                    "command": "rm -rf /",
                    "user_inputs": [],
                    "requires_admin": True,
                    "description": "Dangerous command",
                }
            ]

            # Process commands
            CommandExecutor.process_commands(commands)

            # Check that execute_command was not called
            mock_execute.assert_not_called()

    def test_process_commands_with_shell_integration(self):
        """Test processing commands with shell integration."""
        with (
            patch(
                "smart_terminal.commands.CommandExecutor.replace_placeholders"
            ) as mock_replace,
            patch(
                "smart_terminal.commands.CommandExecutor.execute_command"
            ) as mock_execute,
            patch(
                "smart_terminal.config.ConfigManager.load_config"
            ) as mock_load_config,
            patch("smart_terminal.shell_integration.ShellIntegration") as mock_shell,
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):
            # Setup mocks
            mock_replace.return_value = "cd /tmp"
            mock_execute.return_value = (
                True,
                "Shell integration: Directory will be changed",
            )
            mock_load_config.return_value = {"shell_integration_enabled": True}

            shell_instance = MagicMock()
            shell_instance.is_shell_integration_active.return_value = False
            shell_instance.check_needs_sourcing.return_value = True
            mock_shell.return_value = shell_instance

            commands = [
                {
                    "command": "cd <dir>",
                    "user_inputs": ["dir"],
                    "requires_admin": False,
                    "description": "Change directory",
                }
            ]

            # Process commands
            CommandExecutor.process_commands(commands)

            # Check that execute_command was called with shell_integration=True
            mock_execute.assert_called_once_with(
                "cd /tmp", False, shell_integration=True
            )

            # Check that shell integration methods were called
            assert shell_instance.is_shell_integration_active.called
            assert shell_instance.check_needs_sourcing.called
