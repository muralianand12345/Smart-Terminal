import unittest
import asyncio
from unittest.mock import patch, MagicMock
from smart_terminal.cli.interactive import run_interactive_mode


class TestInteractiveMode(unittest.TestCase):
    @patch("builtins.input", side_effect=["help", "exit"])
    @patch("smart_terminal.cli.interactive.print")
    @patch("smart_terminal.cli.interactive.print_banner")
    @patch("smart_terminal.cli.interactive.Colors")
    def test_run_interactive_mode(
        self, mock_colors, mock_print_banner, mock_print, mock_input
    ):
        terminal = MagicMock()
        config = {"shell_integration_enabled": False}
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_interactive_mode(terminal, config, quiet=False))
        mock_print_banner.assert_called_once()
        mock_print.assert_any_call(
            mock_colors.highlight("SmartTerminal Interactive Mode")
        )
        mock_print.assert_any_call(
            mock_colors.info("Type 'exit' or 'quit' to exit, 'help' for help")
        )
        mock_print.assert_any_call(
            mock_colors.highlight("==============================")
        )
