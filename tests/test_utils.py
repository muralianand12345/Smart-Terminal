"""
Tests for the utils module.
"""

import io
import logging
import pytest
from unittest.mock import patch, MagicMock

from smart_terminal.utils import (
    Colors,
    setup_logging,
    print_error,
    print_banner,
    parse_command_args,
)


class TestColors:
    """Tests for the Colors class."""

    def test_error(self):
        """Test error color formatting."""
        assert Colors.error("test") == "\033[91mtest\033[0m"

    def test_success(self):
        """Test success color formatting."""
        assert Colors.success("test") == "\033[92mtest\033[0m"

    def test_warning(self):
        """Test warning color formatting."""
        assert Colors.warning("test") == "\033[93mtest\033[0m"

    def test_info(self):
        """Test info color formatting."""
        assert Colors.info("test") == "\033[94mtest\033[0m"

    def test_cmd(self):
        """Test command color formatting."""
        assert Colors.cmd("test") == "\033[96mtest\033[0m"

    def test_highlight(self):
        """Test highlight color formatting."""
        assert Colors.highlight("test") == "\033[1mtest\033[0m"


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_setup_logging_debug(self):
        """Test setting up logging at DEBUG level."""
        logger = logging.getLogger("smartterminal")
        logger.handlers = []  # Clear handlers

        with patch("logging.StreamHandler") as mock_handler:
            mock_handler.return_value = MagicMock()
            setup_logging("DEBUG")

            assert logger.level == logging.DEBUG
            assert mock_handler.called

            # Check httpx logger
            httpx_logger = logging.getLogger("httpx")
            assert httpx_logger.level == logging.INFO

    def test_setup_logging_info(self):
        """Test setting up logging at INFO level."""
        logger = logging.getLogger("smartterminal")
        logger.handlers = []  # Clear handlers

        setup_logging("INFO")

        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.Handler)

        # Check httpx logger
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level == logging.WARNING


class TestPrintUtilities:
    """Tests for print utility functions."""

    def test_print_error(self):
        """Test print_error function."""
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout:
            print_error("test error")
            assert Colors.error("Error: test error") in fake_stdout.getvalue()

    def test_print_banner(self):
        """Test print_banner function."""
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout:
            print_banner()
            output = fake_stdout.getvalue()
            assert "SmartTerminal" in output
            assert "AI-Powered Terminal Commands" in output


class TestParseCommandArgs:
    """Tests for the parse_command_args function."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON arguments."""
        args_json = '{"command": "ls", "user_inputs": [], "requires_admin": false}'
        args = parse_command_args(args_json)

        assert args["command"] == "ls"
        assert args["user_inputs"] == []
        assert args["requires_admin"] is False

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON arguments."""
        with pytest.raises(ValueError):
            parse_command_args("invalid json")
