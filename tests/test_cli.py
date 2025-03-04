"""
Tests for the cli module.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from smart_terminal.cli import (
    parse_arguments,
    run_setup,
    run_interactive_mode,
    run_single_command,
    main,
)


class TestCLI:
    """Tests for the CLI module functions."""

    def test_parse_arguments(self):
        """Test parsing command-line arguments."""
        # Test with no arguments
        with patch("sys.argv", ["st"]):
            args = parse_arguments()
            assert args.command is None
            assert not args.setup
            assert not args.clear_history
            assert not args.interactive
            assert not args.debug
            assert not args.version

        # Test with command
        with patch("sys.argv", ["st", "list files"]):
            args = parse_arguments()
            assert args.command == "list files"

        # Test with flags
        with patch("sys.argv", ["st", "--setup"]):
            args = parse_arguments()
            assert args.setup

        with patch("sys.argv", ["st", "--clear-history"]):
            args = parse_arguments()
            assert args.clear_history

        with patch("sys.argv", ["st", "-i"]):
            args = parse_arguments()
            assert args.interactive

        with patch("sys.argv", ["st", "--debug"]):
            args = parse_arguments()
            assert args.debug

        with patch("sys.argv", ["st", "-v"]):
            args = parse_arguments()
            assert args.version

    def test_run_setup(self):
        """Test running the setup function."""
        mock_terminal = MagicMock()

        # Test successful setup
        run_setup(mock_terminal)
        mock_terminal.setup.assert_called_once()

        # Test setup with config error
        from smart_terminal.config import ConfigError

        mock_terminal.setup.side_effect = ConfigError("Config error")

        with patch("smart_terminal.cli.print_error") as mock_print_error:
            run_setup(mock_terminal)
            mock_print_error.assert_called_once_with("Config error")

        # Test setup with unexpected error
        mock_terminal.setup.side_effect = Exception("Unexpected error")

        with (
            patch("smart_terminal.cli.print_error") as mock_print_error,
            patch("smart_terminal.cli.logger.error") as mock_logger_error,
        ):
            run_setup(mock_terminal)
            mock_print_error.assert_called_once_with("Setup failed: Unexpected error")
            mock_logger_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_interactive_mode(self):
        """Test running in interactive mode."""
        mock_terminal = MagicMock()
        mock_terminal.run_interactive = AsyncMock()

        # Test successful interactive mode
        await run_interactive_mode(mock_terminal)
        mock_terminal.run_interactive.assert_called_once()

        # Test keyboard interrupt
        mock_terminal.run_interactive.side_effect = KeyboardInterrupt()

        with patch("smart_terminal.cli.print") as mock_print:
            await run_interactive_mode(mock_terminal)
            assert mock_print.call_count > 0

        # Test other exceptions
        mock_terminal.run_interactive.side_effect = Exception("Interactive error")

        with (
            patch("smart_terminal.cli.print_error") as mock_print_error,
            patch("smart_terminal.cli.logger.error") as mock_logger_error,
        ):
            await run_interactive_mode(mock_terminal)
            mock_print_error.assert_called_once_with(
                "An error occurred: Interactive error"
            )
            mock_logger_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_single_command(self):
        """Test running a single command."""
        mock_terminal = MagicMock()
        mock_terminal.run_command = AsyncMock()

        # Test successful command execution
        await run_single_command(mock_terminal, "list files")
        mock_terminal.run_command.assert_called_once_with("list files")

        # Test error handling
        mock_terminal.run_command.side_effect = Exception("Command error")

        with (
            patch("smart_terminal.cli.print_error") as mock_print_error,
            patch("smart_terminal.cli.logger.error") as mock_logger_error,
        ):
            await run_single_command(mock_terminal, "list files")
            mock_print_error.assert_called_once_with("An error occurred: Command error")
            mock_logger_error.assert_called_once()

    def test_main_version(self):
        """Test main function with --version flag."""
        with (
            patch("smart_terminal.cli.parse_arguments") as mock_parse_args,
            patch("smart_terminal.cli.print") as mock_print,
            patch("smart_terminal.__version__", "1.2.0"),
        ):
            mock_args = MagicMock()
            mock_args.version = True
            mock_parse_args.return_value = mock_args

            result = main()

            assert result == 0
            mock_print.assert_called_once()
            assert "1.2.0" in mock_print.call_args[0][0]

    def test_main_clear_history(self):
        """Test main function with --clear-history flag."""
        with (
            patch("smart_terminal.cli.parse_arguments") as mock_parse_args,
            patch("smart_terminal.cli.ConfigManager.reset_history") as mock_reset,
            patch("smart_terminal.cli.print") as mock_print,
        ):
            mock_args = MagicMock()
            mock_args.version = False
            mock_args.clear_history = True
            mock_parse_args.return_value = mock_args

            result = main()

            assert result == 0
            mock_reset.assert_called_once()
            mock_print.assert_called_once()

    def test_main_setup(self):
        """Test main function with --setup flag."""
        with (
            patch("smart_terminal.cli.parse_arguments") as mock_parse_args,
            patch("smart_terminal.cli.ConfigManager.init_config") as mock_init,
            patch("smart_terminal.cli.SmartTerminal") as mock_terminal_class,
            patch("smart_terminal.cli.run_setup") as mock_run_setup,
            patch("smart_terminal.cli.setup_logging"),
        ):
            mock_args = MagicMock()
            mock_args.version = False
            mock_args.clear_history = False
            mock_args.setup = True
            mock_args.debug = False
            mock_parse_args.return_value = mock_args

            # Setup mock terminal instance
            mock_terminal = MagicMock()
            mock_terminal_class.return_value = mock_terminal

            result = main()

            assert result == 0
            mock_init.assert_called_once()
            mock_terminal_class.assert_called_once()
            mock_run_setup.assert_called_once_with(mock_terminal)

    def test_main_config_error(self):
        """Test main function with configuration error."""
        from smart_terminal.config import ConfigError

        with (
            patch("smart_terminal.cli.parse_arguments") as mock_parse_args,
            patch(
                "smart_terminal.cli.ConfigManager.init_config",
                side_effect=ConfigError("Config error"),
            ),
            patch("smart_terminal.cli.print_error") as mock_print_error,
        ):
            mock_args = MagicMock()
            mock_args.version = False
            mock_args.clear_history = False
            mock_parse_args.return_value = mock_args

            result = main()

            assert result == 1
            mock_print_error.assert_called_once_with(
                "Configuration error: Config error"
            )

    def test_main_api_key_check(self):
        """Test main function with API key check."""
        with (
            patch("smart_terminal.cli.parse_arguments") as mock_parse_args,
            patch("smart_terminal.cli.ConfigManager.init_config"),
            patch("smart_terminal.cli.ConfigManager.load_config") as mock_load_config,
            patch("smart_terminal.cli.print") as mock_print,
        ):
            mock_args = MagicMock()
            mock_args.version = False
            mock_args.clear_history = False
            mock_args.setup = False
            mock_args.interactive = True
            mock_parse_args.return_value = mock_args

            # Return config with no API key
            mock_load_config.return_value = {"api_key": ""}

            result = main()

            assert result == 1
            mock_print.assert_called_once()
            assert "API key not set" in mock_print.call_args[0][0]

    @pytest.mark.asyncio
    async def test_main_interactive_mode(self):
        """Test main function in interactive mode."""
        with (
            patch("smart_terminal.cli.parse_arguments") as mock_parse_args,
            patch("smart_terminal.cli.ConfigManager.init_config"),
            patch("smart_terminal.cli.ConfigManager.load_config") as mock_load_config,
            patch("smart_terminal.cli.SmartTerminal") as mock_terminal_class,
            patch("smart_terminal.cli.asyncio.run") as mock_asyncio_run,
            patch("smart_terminal.cli.setup_logging"),
        ):
            mock_args = MagicMock()
            mock_args.version = False
            mock_args.clear_history = False
            mock_args.setup = False
            mock_args.interactive = True
            mock_args.command = None
            mock_parse_args.return_value = mock_args

            # Return config with API key
            mock_load_config.return_value = {"api_key": "test_key"}

            # Setup mock terminal instance
            mock_terminal = MagicMock()
            mock_terminal_class.return_value = mock_terminal

            result = main()

            assert result == 0
            mock_terminal_class.assert_called_once()
            mock_asyncio_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_single_command(self):
        """Test main function with a single command."""
        with (
            patch("smart_terminal.cli.parse_arguments") as mock_parse_args,
            patch("smart_terminal.cli.ConfigManager.init_config"),
            patch("smart_terminal.cli.ConfigManager.load_config") as mock_load_config,
            patch("smart_terminal.cli.SmartTerminal") as mock_terminal_class,
            patch("smart_terminal.cli.asyncio.run") as mock_asyncio_run,
            patch("smart_terminal.cli.setup_logging"),
        ):
            mock_args = MagicMock()
            mock_args.version = False
            mock_args.clear_history = False
            mock_args.setup = False
            mock_args.interactive = False
            mock_args.command = "list files"
            mock_parse_args.return_value = mock_args

            # Return config with API key
            mock_load_config.return_value = {"api_key": "test_key"}

            # Setup mock terminal instance
            mock_terminal = MagicMock()
            mock_terminal_class.return_value = mock_terminal

            result = main()

            assert result == 0
            mock_terminal_class.assert_called_once()
            mock_asyncio_run.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """Test main function with keyboard interrupt."""
        with (
            patch(
                "smart_terminal.cli.parse_arguments", side_effect=KeyboardInterrupt()
            ),
            patch("smart_terminal.cli.print") as mock_print,
        ):
            result = main()

            assert result == 0
            mock_print.assert_called_once()
            assert "Operation cancelled" in mock_print.call_args[0][0]

    def test_main_unexpected_error(self):
        """Test main function with unexpected error."""
        with (
            patch(
                "smart_terminal.cli.parse_arguments",
                side_effect=Exception("Unexpected error"),
            ),
            patch("smart_terminal.cli.print_error") as mock_print_error,
            patch("smart_terminal.cli.logger.error") as mock_logger_error,
        ):
            result = main()

            assert result == 1
            mock_print_error.assert_called_once_with(
                "An error occurred: Unexpected error"
            )
            mock_logger_error.assert_called_once()
