"""
Shell integration module for SmartTerminal.

This module adds the ability to emit commands that will affect the parent shell's
environment, particularly for directory changes and environment variables.
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import List

# Setup logging
logger = logging.getLogger("smartterminal.shell_integration")


class ShellIntegration:
    """
    Shell integration for SmartTerminal.

    This class manages integration with the parent shell by creating
    a command file that can be sourced by the parent shell to execute
    commands that modify the shell's environment.
    """

    def __init__(self):
        """Initialize shell integration component."""
        self.shell_history_dir = Path.home() / ".smartterminal" / "shell_history"
        self.shell_history_dir.mkdir(exist_ok=True, parents=True)
        self.command_file = self.shell_history_dir / "last_commands.sh"
        self.marker_file = self.shell_history_dir / "needs_sourcing"

    def write_shell_commands(self, commands: List[str], description: str = "") -> str:
        """
        Write commands to a file that can be sourced by the parent shell.

        Args:
            commands: List of shell commands to execute
            description: Optional description of what the commands do

        Returns:
            str: Path to the command file
        """
        try:
            with open(self.command_file, "w") as f:
                f.write("#!/bin/bash\n\n")

                if description:
                    f.write(f"# {description}\n\n")

                for cmd in commands:
                    f.write(f"{cmd}\n")

                # Add command to update status marker
                f.write("\n# Remove the marker file after successful execution\n")
                f.write(f"rm -f {self.marker_file}\n")

            # Make the file executable
            os.chmod(self.command_file, 0o755)

            # Create marker file to indicate commands need sourcing
            with open(self.marker_file, "w") as f:
                f.write("1")

            return str(self.command_file)

        except Exception as e:
            logger.error(f"Failed to write shell commands: {e}")
            return ""

    def clear_needs_sourcing(self) -> None:
        """
        Clear the needs_sourcing marker file.
        This is used when the shell integration function has automatically
        sourced the commands or when we don't need to show the reminder.
        """
        try:
            if self.marker_file.exists():
                self.marker_file.unlink()
                logger.debug("Cleared needs_sourcing marker file")
        except Exception as e:
            logger.error(f"Failed to clear needs_sourcing marker: {e}")

    def check_needs_sourcing(self) -> bool:
        """
        Check if there are commands that need to be sourced.

        Returns:
            bool: True if there are commands that need to be sourced
        """
        return self.marker_file.exists()

    def is_shell_integration_active(self) -> bool:
        """
        Check if shell integration is actively working in the current shell session.

        Returns:
            bool: True if shell integration is working
        """
        try:
            # Write a test file
            test_marker = self.shell_history_dir / "test_integration"
            with open(test_marker, "w") as f:
                f.write("1")

            # Write a test command that removes the test marker
            test_cmd = f"rm -f {test_marker}"
            self.write_shell_commands([test_cmd], "Test shell integration")

            # If shell integration is working, calling the st command would trigger
            # the shell function which would source the command file and remove the test marker
            # We'll simulate that by running the shell function directly
            shell_type = os.environ.get("SHELL", "")
            if "zsh" in shell_type:
                cmd = (
                    "source ~/.zshrc && smart_terminal_integration 2>/dev/null || true"
                )
            elif "bash" in shell_type:
                cmd = (
                    "source ~/.bashrc && smart_terminal_integration 2>/dev/null || true"
                )
            else:
                # If we can't determine shell type, assume integration is not working
                return False

            # Run the shell function
            subprocess.run(cmd, shell=True, stderr=subprocess.PIPE)

            # Check if the test marker was removed
            is_active = not test_marker.exists()

            # Clean up if test failed
            if test_marker.exists():
                test_marker.unlink()

            # Clean up the needs_sourcing marker
            if is_active and self.marker_file.exists():
                self.marker_file.unlink()

            return is_active

        except Exception as e:
            logger.error(f"Error checking shell integration: {e}")
            return False

    def get_shell_integration_script(self) -> str:
        """
        Get the shell integration script for the user's shell.

        This script should be added to the user's shell initialization files
        (e.g., .bashrc, .zshrc) to enable auto-sourcing of generated commands.

        Returns:
            str: Shell integration script
        """
        return """
# SmartTerminal shell integration
function smart_terminal_integration() {
    # Check if there are commands to source
    if [ -f "$HOME/.smartterminal/shell_history/needs_sourcing" ]; then
        source "$HOME/.smartterminal/shell_history/last_commands.sh"
    fi
}

# Alias the st command to include shell integration
function st() {
    command st "$@"
    smart_terminal_integration
}
"""

    @staticmethod
    def get_setup_instructions() -> str:
        """
        Get instructions for setting up shell integration.

        Returns:
            str: Setup instructions
        """
        return """
To enable SmartTerminal shell integration, add the following to your shell's
configuration file (.bashrc, .zshrc, etc.):

# SmartTerminal shell integration
function smart_terminal_integration() {
    # Check if there are commands to source
    if [ -f "$HOME/.smartterminal/shell_history/needs_sourcing" ]; then
        source "$HOME/.smartterminal/shell_history/last_commands.sh"
    fi
}

# Alias the st command to include shell integration
function st() {
    command st "$@"
    smart_terminal_integration
}

After adding this, restart your shell or source your configuration file.
"""
