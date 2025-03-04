"""
Tests for the shell_integration module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from smart_terminal.shell_integration import ShellIntegration


class TestShellIntegration:
    """Tests for ShellIntegration class."""

    @pytest.fixture
    def mock_paths(self):
        """Setup mock paths for testing."""
        with (
            patch.object(Path, "home") as mock_home,
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists") as mock_exists,
        ):
            mock_home.return_value = Path("/home/testuser")
            mock_mkdir.return_value = None
            mock_exists.return_value = False

            yield

    def test_init(self, mock_paths):
        """Test ShellIntegration initialization."""
        shell = ShellIntegration()

        # Check paths
        assert shell.shell_history_dir == Path(
            "/home/testuser/.smartterminal/shell_history"
        )
        assert shell.command_file == Path(
            "/home/testuser/.smartterminal/shell_history/last_commands.sh"
        )
        assert shell.marker_file == Path(
            "/home/testuser/.smartterminal/shell_history/needs_sourcing"
        )

    def test_write_shell_commands(self, mock_paths):
        """Test writing shell commands to a file."""
        shell = ShellIntegration()

        # Test with mocked open
        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch("os.chmod") as mock_chmod,
        ):
            commands = ["cd /tmp", "ls -la"]
            description = "Test commands"

            result = shell.write_shell_commands(commands, description)

            # Check that the file was written correctly
            mock_file.assert_any_call(shell.command_file, "w")
            file_handle = mock_file()

            # Check that description is included
            file_handle.write.assert_any_call("# Test commands\n\n")

            # Check each command
            file_handle.write.assert_any_call("cd /tmp\n")
            file_handle.write.assert_any_call("ls -la\n")

            # Check marker file creation
            mock_file.assert_any_call(shell.marker_file, "w")

            # Check chmod call
            mock_chmod.assert_called_once_with(shell.command_file, 0o755)

            # Check return value
            assert result == str(shell.command_file)

    def test_write_shell_commands_error(self, mock_paths):
        """Test error handling when writing shell commands."""
        shell = ShellIntegration()

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = shell.write_shell_commands(["test"], "test")
            assert result == ""

    def test_clear_needs_sourcing(self, mock_paths):
        """Test clearing the needs_sourcing marker file."""
        shell = ShellIntegration()

        with (
            patch.object(Path, "exists") as mock_exists,
            patch.object(Path, "unlink") as mock_unlink,
        ):
            # Test when file exists
            mock_exists.return_value = True

            shell.clear_needs_sourcing()

            mock_exists.assert_called_once_with()
            mock_unlink.assert_called_once_with()

    def test_clear_needs_sourcing_no_file(self, mock_paths):
        """Test clearing when marker file doesn't exist."""
        shell = ShellIntegration()

        with (
            patch.object(Path, "exists") as mock_exists,
            patch.object(Path, "unlink") as mock_unlink,
        ):
            # Test when file doesn't exist
            mock_exists.return_value = False

            shell.clear_needs_sourcing()

            mock_exists.assert_called_once_with()
            mock_unlink.assert_not_called()

    def test_clear_needs_sourcing_error(self, mock_paths):
        """Test error handling when clearing marker file."""
        shell = ShellIntegration()

        with (
            patch.object(Path, "exists") as mock_exists,
            patch.object(Path, "unlink", side_effect=PermissionError()),
        ):
            mock_exists.return_value = True

            # Should not raise exception
            shell.clear_needs_sourcing()

    def test_check_needs_sourcing(self, mock_paths):
        """Test checking if there are commands that need sourcing."""
        shell = ShellIntegration()

        with patch.object(Path, "exists") as mock_exists:
            # Test when file exists
            mock_exists.return_value = True
            assert shell.check_needs_sourcing() is True

            # Test when file doesn't exist
            mock_exists.return_value = False
            assert shell.check_needs_sourcing() is False

    def test_is_shell_integration_active_not_working(self, mock_paths):
        """Test when shell integration is not working."""
        shell = ShellIntegration()

        # Create a MagicMock for test_marker that always exists (showing integration not working)
        test_marker_mock = MagicMock()
        # Always return True to indicate the marker still exists after subprocess.run
        test_marker_mock.exists.return_value = True
        test_marker_mock.__str__.return_value = "/test_marker_path"

        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch("subprocess.run") as mock_run,
            patch.object(Path, "unlink") as mock_unlink,
            patch("pathlib.Path.__truediv__") as mock_truediv,
            patch.object(shell, "write_shell_commands") as mock_write,
            patch.dict(os.environ, {"SHELL": "/bin/bash"}),
        ):
            # Configure truediv to return our test_marker_mock
            mock_truediv.return_value = test_marker_mock

            # Configure run to return a MagicMock with returncode 0
            mock_run.return_value = MagicMock(returncode=0)

            # Run the method
            result = shell.is_shell_integration_active()
            assert result is False

            # The test_marker should be unlinked as cleanup
            test_marker_mock.unlink.assert_called_once()

    def test_is_shell_integration_active_unknown_shell(self, mock_paths):
        """Test with unknown shell type."""
        shell = ShellIntegration()

        with patch.dict(os.environ, {"SHELL": "/bin/unknown"}):
            result = shell.is_shell_integration_active()
            assert result is False

    def test_is_shell_integration_active_error(self, mock_paths):
        """Test error handling."""
        shell = ShellIntegration()

        with patch("builtins.open", side_effect=Exception("Test error")):
            result = shell.is_shell_integration_active()
            assert result is False

    def test_get_shell_integration_script(self):
        """Test getting the shell integration script."""
        shell = ShellIntegration()
        script = shell.get_shell_integration_script()

        # Check script content
        assert "function smart_terminal_integration()" in script
        assert 'source "$HOME/.smartterminal/shell_history/last_commands.sh"' in script
        assert "function st()" in script

    def test_get_setup_instructions(self):
        """Test getting setup instructions."""
        shell = ShellIntegration()
        instructions = shell.get_setup_instructions()

        # Check instruction content - fix the expected text
        assert "To enable SmartTerminal shell integration" in instructions
        assert "function smart_terminal_integration()" in instructions
        assert "function st()" in instructions
        assert "configuration file (.bashrc, .zshrc, etc.)" in instructions
