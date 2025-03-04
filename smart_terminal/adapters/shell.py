"""
Shell adapters for SmartTerminal.

This module provides adapter interfaces and implementations for
different shell environments, such as bash, zsh, and Windows shells.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Type

# Setup logging
logger = logging.getLogger(__name__)


class ShellAdapter(ABC):
    """
    Abstract adapter interface for shell environments.

    This class defines the interface that all shell adapters must
    implement, allowing the application to work with different
    shell environments consistently.
    """

    @property
    @abstractmethod
    def shell_type(self) -> str:
        """Get the shell type (e.g., 'bash', 'zsh', 'cmd', 'powershell')."""
        pass

    @abstractmethod
    def execute_command(
        self, command: str, requires_admin: bool = False, capture_output: bool = True
    ) -> Tuple[bool, str]:
        """
        Execute a shell command and return the result.

        Args:
            command: Command to execute
            requires_admin: Whether the command requires administrator privileges
            capture_output: Whether to capture and return the command output

        Returns:
            Tuple of (success, output/error message)
        """
        pass

    @abstractmethod
    def write_environment_command(
        self, commands: List[str], description: str = ""
    ) -> str:
        """
        Write commands that affect the shell environment.

        Args:
            commands: List of commands to write
            description: Optional description

        Returns:
            Path to the command file
        """
        pass

    @abstractmethod
    def get_integration_script(self) -> str:
        """
        Get the shell integration script.

        Returns:
            Shell integration script
        """
        pass

    @abstractmethod
    def is_integration_active(self) -> bool:
        """
        Check if shell integration is active.

        Returns:
            True if shell integration is active, False otherwise
        """
        pass

    @classmethod
    @abstractmethod
    def is_supported(cls) -> bool:
        """
        Check if this shell type is supported on the current system.

        Returns:
            True if supported, False otherwise
        """
        pass


class BashAdapter(ShellAdapter):
    """
    Adapter for Bash shell.

    This adapter implements the ShellAdapter interface for
    the Bash shell, common on Linux and macOS.
    """

    def __init__(self):
        """Initialize Bash adapter."""
        self.shell_history_dir = Path.home() / ".smartterminal" / "shell_history"
        self.shell_history_dir.mkdir(exist_ok=True, parents=True)
        self.command_file = self.shell_history_dir / "last_commands.sh"
        self.marker_file = self.shell_history_dir / "needs_sourcing"

    @property
    def shell_type(self) -> str:
        """Get the shell type."""
        return "bash"

    def execute_command(
        self, command: str, requires_admin: bool = False, capture_output: bool = True
    ) -> Tuple[bool, str]:
        """
        Execute a shell command and return the result.

        Args:
            command: Command to execute
            requires_admin: Whether the command requires administrator privileges
            capture_output: Whether to capture and return the command output

        Returns:
            Tuple of (success, output/error message)
        """
        try:
            logger.debug(
                f"Executing command: {command}, requires_admin={requires_admin}"
            )

            if requires_admin:
                command = f"sudo {command}"

            if capture_output:
                result = subprocess.run(
                    command,
                    shell=True,
                    executable="/bin/bash",
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    logger.debug("Command executed successfully")
                    return True, result.stdout
                else:
                    logger.error(
                        f"Command failed with return code {result.returncode}: {result.stderr}"
                    )
                    return False, result.stderr
            else:
                # Execute without capturing output
                result = subprocess.run(command, shell=True, executable="/bin/bash")

                return (
                    result.returncode == 0,
                    f"Command exited with code {result.returncode}",
                )

        except Exception as e:
            logger.error(f"Exception while executing command: {e}")
            return False, f"Command execution failed: {e}"

    def write_environment_command(
        self, commands: List[str], description: str = ""
    ) -> str:
        """
        Write commands that affect the shell environment.

        Args:
            commands: List of commands to write
            description: Optional description

        Returns:
            Path to the command file
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

    def get_integration_script(self) -> str:
        """
        Get the shell integration script.

        Returns:
            Shell integration script
        """
        return """
# SmartTerminal shell integration for Bash
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

    def is_integration_active(self) -> bool:
        """
        Check if shell integration is active.

        Returns:
            True if shell integration is active, False otherwise
        """
        try:
            # Write a test file
            test_marker = self.shell_history_dir / "test_integration"
            with open(test_marker, "w") as f:
                f.write("1")

            # Write a test command that removes the test marker
            test_cmd = f"rm -f {test_marker}"
            self.write_environment_command([test_cmd], "Test shell integration")

            # Run the shell function
            cmd = "source ~/.bashrc && smart_terminal_integration 2>/dev/null || true"
            subprocess.run(cmd, shell=True, stderr=subprocess.PIPE)

            # Check if the test marker was removed
            is_active = not test_marker.exists()

            # Clean up if test failed
            if test_marker.exists():
                test_marker.unlink()

            # Clean up the needs_sourcing marker if integration is active
            if is_active and self.marker_file.exists():
                self.marker_file.unlink()

            return is_active

        except Exception as e:
            logger.error(f"Error checking shell integration: {e}")
            return False

    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if Bash is supported on the current system.

        Returns:
            True if supported, False otherwise
        """
        try:
            result = subprocess.run(
                ["bash", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return result.returncode == 0
        except Exception:
            return False


class ZshAdapter(ShellAdapter):
    """
    Adapter for Zsh shell.

    This adapter implements the ShellAdapter interface for
    the Zsh shell, common on macOS and some Linux distributions.
    """

    def __init__(self):
        """Initialize Zsh adapter."""
        self.shell_history_dir = Path.home() / ".smartterminal" / "shell_history"
        self.shell_history_dir.mkdir(exist_ok=True, parents=True)
        self.command_file = self.shell_history_dir / "last_commands.sh"
        self.marker_file = self.shell_history_dir / "needs_sourcing"

    @property
    def shell_type(self) -> str:
        """Get the shell type."""
        return "zsh"

    def execute_command(
        self, command: str, requires_admin: bool = False, capture_output: bool = True
    ) -> Tuple[bool, str]:
        """
        Execute a shell command and return the result.

        Args:
            command: Command to execute
            requires_admin: Whether the command requires administrator privileges
            capture_output: Whether to capture and return the command output

        Returns:
            Tuple of (success, output/error message)
        """
        try:
            logger.debug(
                f"Executing command: {command}, requires_admin={requires_admin}"
            )

            if requires_admin:
                command = f"sudo {command}"

            if capture_output:
                result = subprocess.run(
                    command,
                    shell=True,
                    executable="/bin/zsh",
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    logger.debug("Command executed successfully")
                    return True, result.stdout
                else:
                    logger.error(
                        f"Command failed with return code {result.returncode}: {result.stderr}"
                    )
                    return False, result.stderr
            else:
                # Execute without capturing output
                result = subprocess.run(command, shell=True, executable="/bin/zsh")

                return (
                    result.returncode == 0,
                    f"Command exited with code {result.returncode}",
                )

        except Exception as e:
            logger.error(f"Exception while executing command: {e}")
            return False, f"Command execution failed: {e}"

    def write_environment_command(
        self, commands: List[str], description: str = ""
    ) -> str:
        """
        Write commands that affect the shell environment.

        Args:
            commands: List of commands to write
            description: Optional description

        Returns:
            Path to the command file
        """
        try:
            with open(self.command_file, "w") as f:
                f.write("#!/bin/zsh\n\n")

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

    def get_integration_script(self) -> str:
        """
        Get the shell integration script.

        Returns:
            Shell integration script
        """
        return """
# SmartTerminal shell integration for Zsh
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

    def is_integration_active(self) -> bool:
        """
        Check if shell integration is active.

        Returns:
            True if shell integration is active, False otherwise
        """
        try:
            # Write a test file
            test_marker = self.shell_history_dir / "test_integration"
            with open(test_marker, "w") as f:
                f.write("1")

            # Write a test command that removes the test marker
            test_cmd = f"rm -f {test_marker}"
            self.write_environment_command([test_cmd], "Test shell integration")

            # Run the shell function
            cmd = "source ~/.zshrc && smart_terminal_integration 2>/dev/null || true"
            subprocess.run(cmd, shell=True, stderr=subprocess.PIPE)

            # Check if the test marker was removed
            is_active = not test_marker.exists()

            # Clean up if test failed
            if test_marker.exists():
                test_marker.unlink()

            # Clean up the needs_sourcing marker if integration is active
            if is_active and self.marker_file.exists():
                self.marker_file.unlink()

            return is_active

        except Exception as e:
            logger.error(f"Error checking shell integration: {e}")
            return False

    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if Zsh is supported on the current system.

        Returns:
            True if supported, False otherwise
        """
        try:
            result = subprocess.run(
                ["zsh", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return result.returncode == 0
        except Exception:
            return False


class PowerShellAdapter(ShellAdapter):
    """
    Adapter for PowerShell on Windows.

    This adapter implements the ShellAdapter interface for
    PowerShell, common on Windows systems.
    """

    def __init__(self):
        """Initialize PowerShell adapter."""
        self.shell_history_dir = Path.home() / ".smartterminal" / "shell_history"
        self.shell_history_dir.mkdir(exist_ok=True, parents=True)
        self.command_file = self.shell_history_dir / "last_commands.ps1"
        self.marker_file = self.shell_history_dir / "needs_sourcing"

    @property
    def shell_type(self) -> str:
        """Get the shell type."""
        return "powershell"

    def execute_command(
        self, command: str, requires_admin: bool = False, capture_output: bool = True
    ) -> Tuple[bool, str]:
        """
        Execute a shell command and return the result.

        Args:
            command: Command to execute
            requires_admin: Whether the command requires administrator privileges
            capture_output: Whether to capture and return the command output

        Returns:
            Tuple of (success, output/error message)
        """
        try:
            logger.debug(
                f"Executing command: {command}, requires_admin={requires_admin}"
            )

            # Prepare PowerShell command
            ps_command = f'powershell -Command "{command}"'

            if requires_admin:
                # For Windows, we can't easily elevate from here
                # Just warn about needing admin privileges
                logger.warning("Command requires administrator privileges")

            if capture_output:
                result = subprocess.run(
                    ps_command, shell=True, capture_output=True, text=True
                )

                if result.returncode == 0:
                    logger.debug("Command executed successfully")
                    return True, result.stdout
                else:
                    logger.error(
                        f"Command failed with return code {result.returncode}: {result.stderr}"
                    )
                    return False, result.stderr
            else:
                # Execute without capturing output
                result = subprocess.run(ps_command, shell=True)
                return (
                    result.returncode == 0,
                    f"Command exited with code {result.returncode}",
                )

        except Exception as e:
            logger.error(f"Exception while executing command: {e}")
            return False, f"Command execution failed: {e}"

    def write_environment_command(
        self, commands: List[str], description: str = ""
    ) -> str:
        """
        Write commands that affect the shell environment.

        Args:
            commands: List of commands to write
            description: Optional description

        Returns:
            Path to the command file
        """
        try:
            with open(self.command_file, "w") as f:
                if description:
                    f.write(f"# {description}\n\n")

                for cmd in commands:
                    f.write(f"{cmd}\n")

                # Add command to update status marker
                f.write("\n# Remove the marker file after successful execution\n")
                f.write(
                    f"Remove-Item -Path '{self.marker_file}' -ErrorAction SilentlyContinue\n"
                )

            # Create marker file to indicate commands need sourcing
            with open(self.marker_file, "w") as f:
                f.write("1")

            return str(self.command_file)

        except Exception as e:
            logger.error(f"Failed to write shell commands: {e}")
            return ""

    def get_integration_script(self) -> str:
        """
        Get the shell integration script.

        Returns:
            Shell integration script
        """
        return """
# SmartTerminal shell integration for PowerShell
function Invoke-SmartTerminalIntegration {
    # Check if there are commands to source
    if (Test-Path "$HOME/.smartterminal/shell_history/needs_sourcing") {
        . "$HOME/.smartterminal/shell_history/last_commands.ps1"
    }
}

# Function to wrap the st command
function st {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        $Params
    )
    
    & st.exe $Params
    Invoke-SmartTerminalIntegration
}
"""

    def is_integration_active(self) -> bool:
        """
        Check if shell integration is active.

        Returns:
            True if shell integration is active, False otherwise
        """
        try:
            # Write a test file
            test_marker = self.shell_history_dir / "test_integration"
            with open(test_marker, "w") as f:
                f.write("1")

            # Write a test command that removes the test marker
            test_cmd = f"Remove-Item -Path '{test_marker}' -Force"
            self.write_environment_command([test_cmd], "Test shell integration")

            # Run the shell function via PowerShell
            cmd = 'powershell -Command ". $PROFILE; Invoke-SmartTerminalIntegration -ErrorAction SilentlyContinue"'
            subprocess.run(cmd, shell=True, stderr=subprocess.PIPE)

            # Check if the test marker was removed
            is_active = not test_marker.exists()

            # Clean up if test failed
            if test_marker.exists():
                test_marker.unlink()

            # Clean up the needs_sourcing marker if integration is active
            if is_active and self.marker_file.exists():
                self.marker_file.unlink()

            return is_active

        except Exception as e:
            logger.error(f"Error checking shell integration: {e}")
            return False

    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if PowerShell is supported on the current system.

        Returns:
            True if supported, False otherwise
        """
        if sys.platform != "win32":
            return False

        try:
            result = subprocess.run(
                ["powershell", "-Command", "echo 'Test'"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return result.returncode == 0
        except Exception:
            return False


class ShellAdapterFactory:
    """
    Factory for creating shell adapters.

    This class provides methods for creating shell adapters based on
    the current environment or specific requirements.
    """

    @staticmethod
    def create_adapter() -> ShellAdapter:
        """
        Create an appropriate shell adapter for the current environment.

        Returns:
            ShellAdapter instance

        Raises:
            RuntimeError: If no suitable shell adapter is available
        """
        # Check for ZSH (common on macOS)
        if ZshAdapter.is_supported():
            # Check if it's the current shell
            current_shell = os.environ.get("SHELL", "")
            if "zsh" in current_shell:
                logger.debug("Using Zsh adapter (current shell)")
                return ZshAdapter()

        # Check for Bash (common on Linux and available on macOS)
        if BashAdapter.is_supported():
            # Check if it's the current shell
            current_shell = os.environ.get("SHELL", "")
            if "bash" in current_shell:
                logger.debug("Using Bash adapter (current shell)")
                return BashAdapter()
            elif not (sys.platform == "win32"):
                logger.debug("Using Bash adapter as fallback")
                return BashAdapter()

        # Check for PowerShell (Windows)
        if PowerShellAdapter.is_supported():
            logger.debug("Using PowerShell adapter")
            return PowerShellAdapter()

        # Fallback to most likely working adapter based on platform
        if sys.platform == "win32":
            logger.debug("Using PowerShell adapter as fallback for Windows")
            return PowerShellAdapter()
        else:
            logger.debug("Using Bash adapter as fallback for Unix-like systems")
            return BashAdapter()

    @staticmethod
    def get_available_adapters() -> Dict[str, Type[ShellAdapter]]:
        """
        Get all available shell adapters on the current system.

        Returns:
            Dictionary mapping shell type to adapter class
        """
        adapters = {}

        if ZshAdapter.is_supported():
            adapters["zsh"] = ZshAdapter

        if BashAdapter.is_supported():
            adapters["bash"] = BashAdapter

        if PowerShellAdapter.is_supported():
            adapters["powershell"] = PowerShellAdapter

        return adapters
