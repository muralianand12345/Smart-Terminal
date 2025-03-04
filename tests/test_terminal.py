"""
Tests for the terminal module.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open

from smart_terminal.terminal import SmartTerminal
from smart_terminal.ai import AIError
from smart_terminal.config import ConfigError


class TestSmartTerminal:
    """Tests for the SmartTerminal class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Setup mock dependencies for SmartTerminal tests."""
        with (
            patch("smart_terminal.terminal.ConfigManager") as mock_config,
            patch("smart_terminal.terminal.AIClient") as mock_ai_client,
            patch("smart_terminal.terminal.CommandGenerator") as mock_cmd_gen,
            patch("smart_terminal.terminal.ShellIntegration") as mock_shell,
        ):
            # Setup mock config
            mock_config.load_config.return_value = {
                "api_key": "test_key",
                "base_url": "test_url",
                "model_name": "test_model",
            }

            # Create mock instances
            mock_ai_client_instance = MagicMock()
            mock_cmd_gen_instance = MagicMock()
            mock_shell_instance = MagicMock()

            # Configure constructor returns
            mock_ai_client.return_value = mock_ai_client_instance
            mock_cmd_gen.return_value = mock_cmd_gen_instance
            mock_shell.return_value = mock_shell_instance

            yield {
                "config": mock_config,
                "ai_client": mock_ai_client,
                "ai_client_instance": mock_ai_client_instance,
                "cmd_gen": mock_cmd_gen,
                "cmd_gen_instance": mock_cmd_gen_instance,
                "shell": mock_shell,
                "shell_instance": mock_shell_instance,
            }

    def test_init(self, mock_dependencies):
        """Test SmartTerminal initialization."""
        terminal = SmartTerminal()

        # Check that the dependencies were initialized correctly
        mock_dependencies["ai_client"].assert_called_with(
            api_key="test_key", base_url="test_url", model_name="test_model"
        )

        mock_dependencies["cmd_gen"].assert_called_with(
            mock_dependencies["ai_client_instance"]
        )

        # Check instance properties
        assert terminal.ai_client == mock_dependencies["ai_client_instance"]
        assert terminal.command_generator == mock_dependencies["cmd_gen_instance"]
        assert terminal.shell_integration == mock_dependencies["shell_instance"]
        assert terminal.current_directory == os.getcwd()
        assert terminal.recent_commands == []
        assert terminal.recent_outputs == []

    def test_init_error(self):
        """Test error handling during initialization."""
        with (
            patch(
                "smart_terminal.terminal.ConfigManager.load_config",
                side_effect=Exception("Config error"),
            ),
            patch("smart_terminal.terminal.print_error") as mock_print_error,
            patch("smart_terminal.terminal.logger.error") as mock_logger_error,
            pytest.raises(Exception),
        ):
            SmartTerminal()

            mock_print_error.assert_called_once()
            mock_logger_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_input_success(self, mock_dependencies):
        """Test successful command processing."""
        terminal = SmartTerminal()

        # Mock command generator to return commands
        tool_call = MagicMock()
        tool_call.function.arguments = (
            '{"command": "ls -la", "user_inputs": [], "description": "List files"}'
        )

        cmd_sets = [[tool_call]]
        mock_dependencies["cmd_gen_instance"].generate_commands = AsyncMock(
            return_value=cmd_sets
        )

        # Mock command executor
        with patch(
            "smart_terminal.terminal.CommandExecutor.process_commands"
        ) as mock_process:
            # Test with empty history
            history = await terminal.process_input("list files")

            # Check that the command generator was called with enhanced query
            mock_dependencies["cmd_gen_instance"].generate_commands.assert_called_once()
            call_args = mock_dependencies[
                "cmd_gen_instance"
            ].generate_commands.call_args[0]
            assert "list files" in call_args[0]
            assert "[CONTEXT]" in call_args[0]

            # Check that the executor was called with commands
            mock_process.assert_called_once()
            assert len(mock_process.call_args[0][0]) == 1

            # Check that history was updated
            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[0]["content"] == "list files"
            assert history[1]["role"] == "assistant"

            # Check that recent commands were updated
            assert len(terminal.recent_commands) == 1
            assert terminal.recent_commands[0] == "ls -la"

    @pytest.mark.asyncio
    async def test_process_input_no_commands(self, mock_dependencies):
        """Test processing when no commands are generated."""
        terminal = SmartTerminal()

        # Mock command generator to return no commands
        mock_dependencies["cmd_gen_instance"].generate_commands = AsyncMock(
            return_value=[]
        )

        with patch("smart_terminal.terminal.print") as mock_print:
            history = await terminal.process_input("invalid command")

            # Verify print was called with the processing message and error message
            assert mock_print.call_count == 2
            assert "Processing: invalid command" in mock_print.call_args_list[0][0][0]
            assert (
                "couldn't determine the commands"
                in mock_print.call_args_list[1][0][0].lower()
            )

            # Check that history was updated with only the user query
            assert len(history) == 1
            assert history[0]["role"] == "user"
            assert history[0]["content"] == "invalid command"

        @pytest.mark.asyncio
        async def test_process_input_invalid_command_format(self, mock_dependencies):
            """Test processing when commands are in invalid format."""
            terminal = SmartTerminal()

            # Mock command generator to return malformed commands
            tool_call = MagicMock()
            tool_call.function.arguments = "invalid json"

            cmd_sets = [[tool_call]]
            mock_dependencies["cmd_gen_instance"].generate_commands = AsyncMock(
                return_value=cmd_sets
            )

            with (
                patch("smart_terminal.terminal.print") as mock_print,
                patch("smart_terminal.terminal.logger.error") as mock_logger_error,
            ):
                history = await terminal.process_input("list files")

                # Verify print was called with the processing message and error message
                assert mock_print.call_count == 2
                assert "Processing: list files" in mock_print.call_args_list[0][0][0]
                assert (
                    "couldn't generate valid commands"
                    in mock_print.call_args_list[1][0][0].lower()
                )

                assert mock_logger_error.called

                # Check that history was updated with only the user query
                assert len(history) == 1
                assert history[0]["role"] == "user"
                assert history[0]["content"] == "list files"

    @pytest.mark.asyncio
    async def test_process_input_environment_changing_commands(self, mock_dependencies):
        """Test processing environment-changing commands."""
        terminal = SmartTerminal()

        # Mock command generator to return cd command
        tool_call = MagicMock()
        tool_call.function.arguments = '{"command": "cd /tmp", "user_inputs": [], "description": "Change directory"}'

        cmd_sets = [[tool_call]]
        mock_dependencies["cmd_gen_instance"].generate_commands = AsyncMock(
            return_value=cmd_sets
        )

        # Mock config to disable shell integration
        mock_dependencies["config"].load_config.return_value = {
            "api_key": "test_key",
            "shell_integration_enabled": False,
        }

        with (
            patch(
                "smart_terminal.terminal.CommandExecutor.process_commands"
            ) as mock_process,
            patch("smart_terminal.terminal.print") as mock_print,
            patch("builtins.input", return_value="n"),
        ):  # Don't set up shell integration
            await terminal.process_input("change to tmp directory")

            # Check that warning was printed
            warning_calls = [
                call
                for call in mock_print.call_args_list
                if "won't persist" in call[0][0].lower()
            ]
            assert len(warning_calls) > 0

            # Check input prompt for shell integration
            assert "set up shell integration" in input.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_process_input_shell_integration_setup(self, mock_dependencies):
        """Test setting up shell integration during command processing."""
        terminal = SmartTerminal()

        # Mock command generator to return cd command
        tool_call = MagicMock()
        tool_call.function.arguments = '{"command": "cd /tmp", "user_inputs": [], "description": "Change directory"}'

        cmd_sets = [[tool_call]]
        mock_dependencies["cmd_gen_instance"].generate_commands = AsyncMock(
            return_value=cmd_sets
        )

        # Mock config
        mock_dependencies["config"].load_config.return_value = {
            "api_key": "test_key",
            "shell_integration_enabled": False,
        }

        with (
            patch(
                "smart_terminal.terminal.CommandExecutor.process_commands"
            ) as mock_process,
            patch("smart_terminal.terminal.print"),
            patch("builtins.input", return_value="y"),
            patch.object(SmartTerminal, "setup_shell_integration") as mock_setup,
        ):
            await terminal.process_input("change to tmp directory")

            # Check that setup was called
            mock_setup.assert_called_once()

            # Check that config was updated
            mock_dependencies["config"].save_config.assert_called_once()
            assert (
                mock_dependencies["config"].save_config.call_args[0][0][
                    "shell_integration_enabled"
                ]
                is True
            )

    @pytest.mark.asyncio
    async def test_process_input_shell_integration_reminder(self, mock_dependencies):
        """Test shell integration reminder when commands need sourcing."""
        terminal = SmartTerminal()

        # Mock command generator to return cd command
        tool_call = MagicMock()
        tool_call.function.arguments = '{"command": "cd /tmp", "user_inputs": [], "description": "Change directory"}'

        cmd_sets = [[tool_call]]
        mock_dependencies["cmd_gen_instance"].generate_commands = AsyncMock(
            return_value=cmd_sets
        )

        # Mock config with shell integration enabled
        mock_dependencies["config"].load_config.return_value = {
            "api_key": "test_key",
            "shell_integration_enabled": True,
        }

        # Mock shell integration status
        mock_dependencies[
            "shell_instance"
        ].is_shell_integration_active.return_value = False
        mock_dependencies["shell_instance"].check_needs_sourcing.return_value = True

        with (
            patch(
                "smart_terminal.terminal.CommandExecutor.process_commands"
            ) as mock_process,
            patch("smart_terminal.terminal.print") as mock_print,
        ):
            await terminal.process_input("change to tmp directory")

            # Check that reminder was printed
            reminder_calls = [
                call
                for call in mock_print.call_args_list
                if "source ~/.smartterminal/shell_history/last_commands.sh"
                in call[0][0]
            ]
            assert len(reminder_calls) > 0

    @pytest.mark.asyncio
    async def test_process_input_ai_error(self, mock_dependencies):
        """Test handling AI errors during command processing."""
        terminal = SmartTerminal()

        # Mock command generator to raise AIError
        mock_dependencies["cmd_gen_instance"].generate_commands = AsyncMock(
            side_effect=AIError("API error")
        )

        with patch("smart_terminal.terminal.print_error") as mock_print_error:
            history = await terminal.process_input("list files")

            mock_print_error.assert_called_once_with("API error")

            # Check that history contains only the user query
            assert len(history) == 1
            assert history[0]["role"] == "user"
            assert history[0]["content"] == "list files"

    @pytest.mark.asyncio
    async def test_process_input_unexpected_error(self, mock_dependencies):
        """Test handling unexpected errors during command processing."""
        terminal = SmartTerminal()

        # Mock command generator to raise unexpected error
        mock_dependencies["cmd_gen_instance"].generate_commands = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with (
            patch("smart_terminal.terminal.print_error") as mock_print_error,
            patch("smart_terminal.terminal.logger.error") as mock_logger_error,
        ):
            history = await terminal.process_input("list files")

            mock_print_error.assert_called_once_with(
                "An unexpected error occurred: Unexpected error"
            )
            mock_logger_error.assert_called_once()

            # Check that history contains only the user query
            assert len(history) == 1
            assert history[0]["role"] == "user"
            assert history[0]["content"] == "list files"

    def test_setup(self, mock_dependencies):
        """Test setup method."""
        terminal = SmartTerminal()

        # Mock config
        mock_dependencies["config"].load_config.return_value = {
            "api_key": "",
            "base_url": "https://api.groq.com/openai/v1",
            "model_name": "llama-3.3-70b-versatile",
            "default_os": "macos",
            "history_limit": 20,
            "log_level": "INFO",
        }

        with (
            patch("smart_terminal.terminal.print_banner"),
            patch("smart_terminal.terminal.print"),
            patch("builtins.input") as mock_input,
        ):
            # Setup input responses
            mock_input.side_effect = [
                "new_api_key",  # API key
                "",  # Base URL (use default)
                "gpt-4",  # Model name
                "linux",  # Default OS
                "30",  # History limit
                "DEBUG",  # Log level
                "y",  # Shell integration
            ]

            # Mock setup_shell_integration
            with patch.object(terminal, "setup_shell_integration") as mock_shell_setup:
                terminal.setup()

                # Check that config was saved with new values
                saved_config = mock_dependencies["config"].save_config.call_args[0][0]
                assert saved_config["api_key"] == "new_api_key"
                assert saved_config["model_name"] == "gpt-4"
                assert saved_config["default_os"] == "linux"
                assert saved_config["history_limit"] == 30
                assert saved_config["log_level"] == "DEBUG"
                assert saved_config["shell_integration_enabled"] is True

                # Check that shell integration setup was called
                mock_shell_setup.assert_called_once()

    def test_setup_config_error(self, mock_dependencies):
        """Test setup with configuration error."""
        terminal = SmartTerminal()

        # Mock config to raise error
        mock_dependencies["config"].load_config.side_effect = ConfigError(
            "Config error"
        )

        with (
            patch("smart_terminal.terminal.print_banner"),
            patch("smart_terminal.terminal.print"),
            patch("smart_terminal.terminal.print_error") as mock_print_error,
        ):
            terminal.setup()

            mock_print_error.assert_called_once_with("Config error")

    def test_setup_unexpected_error(self, mock_dependencies):
        """Test setup with unexpected error."""
        terminal = SmartTerminal()

        # Mock config to raise unexpected error
        mock_dependencies["config"].load_config.side_effect = Exception(
            "Unexpected error"
        )

        with (
            patch("smart_terminal.terminal.print_banner"),
            patch("smart_terminal.terminal.print"),
            patch("smart_terminal.terminal.print_error") as mock_print_error,
            patch("smart_terminal.terminal.logger.error") as mock_logger_error,
        ):
            terminal.setup()

            mock_print_error.assert_called_once_with("Setup failed: Unexpected error")
            mock_logger_error.assert_called_once()

    def test_setup_shell_integration(self, mock_dependencies):
        """Test setting up shell integration."""
        terminal = SmartTerminal()

        # Get shell integration script
        mock_dependencies[
            "shell_instance"
        ].get_shell_integration_script.return_value = "shell script"

        with (
            patch("smart_terminal.terminal.print"),
            patch("os.environ", {"SHELL": "/bin/bash"}),
            patch("os.path.exists") as mock_exists,
            patch("builtins.open", mock_open()) as mock_file,
            patch("builtins.input", return_value="y"),
            patch.object(
                terminal.shell_integration, "write_shell_commands"
            ) as mock_write_shell_commands,
        ):
            mock_exists.return_value = True

            terminal.setup_shell_integration()

            # Check if shell script was checked for existing integration
            mock_file.assert_any_call(os.path.expanduser("~/.bashrc"), "r")

            # Check if script was written to file
            mock_file().write.assert_any_call("\n# Added by SmartTerminal setup\n")
            mock_file().write.assert_any_call("shell script")

            # Check that test commands were written
            mock_write_shell_commands.assert_called_once_with(
                ["echo 'Shell integration is working!'", 'cd "$(pwd)"'],
                "Test shell integration",
            )

    def test_setup_shell_integration_file_not_found(self, mock_dependencies):
        """Test shell integration setup when config file not found."""
        terminal = SmartTerminal()

        with (
            patch("smart_terminal.terminal.print"),
            patch("os.environ", {"SHELL": "/bin/bash"}),
            patch("os.path.exists") as mock_exists,
            patch("builtins.input", return_value="y"),
        ):
            mock_exists.return_value = False

            terminal.setup_shell_integration()

            # Shell integration should still create test commands
            mock_dependencies[
                "shell_instance"
            ].write_shell_commands.assert_called_once()

    def test_setup_shell_integration_existing_integration(self, mock_dependencies):
        """Test setup when shell integration already exists."""
        terminal = SmartTerminal()

        with (
            patch("smart_terminal.terminal.print"),
            patch("os.environ", {"SHELL": "/bin/bash"}),
            patch("os.path.exists") as mock_exists,
            patch(
                "builtins.open", mock_open(read_data="smart_terminal_integration")
            ) as mock_file,
            patch("builtins.input", return_value="y"),
        ):
            mock_exists.return_value = True

            terminal.setup_shell_integration()

            # Should not write to config file again
            write_calls = [
                call
                for call in mock_file().write.call_args_list
                if "# Added by SmartTerminal setup" in call[0]
            ]
            assert len(write_calls) == 0

    def test_setup_shell_integration_error(self, mock_dependencies):
        """Test error handling in shell integration setup."""
        terminal = SmartTerminal()

        with (
            patch("smart_terminal.terminal.print"),
            patch("os.environ", {"SHELL": "/bin/bash"}),
            patch("builtins.open", side_effect=Exception("File error")),
            patch("smart_terminal.terminal.logger.error") as mock_logger_error,
            patch("builtins.input", return_value="y"),
        ):
            terminal.setup_shell_integration()

            # Should log error but not crash
            mock_logger_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_interactive(self, mock_dependencies):
        """Test running in interactive mode."""
        terminal = SmartTerminal()

        # Mock history and config
        mock_dependencies["config"].load_history.return_value = []
        mock_dependencies["config"].load_config.return_value = {
            "api_key": "test_key",
            "shell_integration_enabled": False,
        }

        with (
            patch("smart_terminal.terminal.print_banner"),
            patch("smart_terminal.terminal.print"),
            patch("builtins.input") as mock_input,
            patch.object(terminal, "process_input") as mock_process,
        ):
            # Setup input responses: one command, then exit
            mock_input.side_effect = ["list files", "exit"]
            mock_process.return_value = [{"role": "user", "content": "list files"}]

            await terminal.run_interactive()

            # Check process_input was called
            mock_process.assert_called_once_with("list files", [])

            # Check history was saved
            mock_dependencies["config"].save_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_interactive_shell_integration_reminder(self, mock_dependencies):
        """Test interactive mode with shell integration reminder."""
        terminal = SmartTerminal()

        # Mock history, config, and shell integration status
        mock_dependencies["config"].load_history.return_value = []
        mock_dependencies["config"].load_config.return_value = {
            "api_key": "test_key",
            "shell_integration_enabled": True,
        }
        mock_dependencies["shell_instance"].check_needs_sourcing.return_value = True

        with (
            patch("smart_terminal.terminal.print_banner"),
            patch("smart_terminal.terminal.print") as mock_print,
            patch("builtins.input") as mock_input,
        ):
            # Setup input to exit immediately
            mock_input.return_value = "exit"

            await terminal.run_interactive()

            # Check that reminder was printed
            reminder_calls = [
                call
                for call in mock_print.call_args_list
                if "source ~/.smartterminal/shell_history/last_commands.sh" in str(call)
            ]
            assert len(reminder_calls) > 0

    @pytest.mark.asyncio
    async def test_run_interactive_keyboard_interrupt(self, mock_dependencies):
        """Test interactive mode with keyboard interrupt."""
        terminal = SmartTerminal()

        # Mock history and config
        mock_dependencies["config"].load_history.return_value = []
        mock_dependencies["config"].load_config.return_value = {
            "api_key": "test_key",
            "shell_integration_enabled": False,
        }

        with (
            patch("smart_terminal.terminal.print_banner"),
            patch("smart_terminal.terminal.print") as mock_print,
            patch("builtins.input", side_effect=KeyboardInterrupt()),
        ):
            await terminal.run_interactive()

            # Check that exit message was printed
            exit_calls = [
                call for call in mock_print.call_args_list if "Exiting..." in str(call)
            ]
            assert len(exit_calls) > 0

    @pytest.mark.asyncio
    async def test_run_interactive_error(self, mock_dependencies):
        """Test error handling in interactive mode."""
        terminal = SmartTerminal()

        # Mock history and config
        mock_dependencies["config"].load_history.return_value = []
        mock_dependencies["config"].load_config.return_value = {
            "api_key": "test_key",
            "shell_integration_enabled": False,
        }

        with (
            patch("smart_terminal.terminal.print_banner"),
            patch("smart_terminal.terminal.print"),
            patch("builtins.input") as mock_input,
            patch.object(
                terminal, "process_input", side_effect=Exception("Process error")
            ),
            patch("smart_terminal.terminal.print_error") as mock_print_error,
            patch("smart_terminal.terminal.logger.error") as mock_logger_error,
        ):
            # Setup input: one command, then exit
            mock_input.side_effect = ["list files", "exit"]

            await terminal.run_interactive()

            # Check error handling
            mock_print_error.assert_called_once_with("An error occurred: Process error")
            mock_logger_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_command(self, mock_dependencies):
        """Test running a single command."""
        terminal = SmartTerminal()

        # Mock history
        mock_dependencies["config"].load_history.return_value = []

        with patch.object(terminal, "process_input") as mock_process:
            # Setup process_input to return updated history
            mock_process.return_value = [
                {"role": "user", "content": "list files"},
                {"role": "assistant", "content": "I executed: ls -la"},
            ]

            await terminal.run_command("list files")

            # Check process_input was called
            mock_process.assert_called_once_with("list files", [])

            # Check history was saved
            mock_dependencies["config"].save_history.assert_called_once_with(
                mock_process.return_value
            )
