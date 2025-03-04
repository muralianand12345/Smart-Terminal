"""
Pytest configuration file for SmartTerminal tests.

This file contains fixtures and configuration settings for tests.
"""

import pytest
import logging
from unittest.mock import patch

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging output during tests."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def temp_config_dir(tmp_path):
    """
    Create a temporary configuration directory for testing.

    This fixture creates a temporary directory structure for config files
    and patches the ConfigManager paths to use it.
    """
    from smart_terminal.config import ConfigManager

    # Create directory structure
    config_dir = tmp_path / ".smartterminal"
    config_dir.mkdir(exist_ok=True)

    shell_history_dir = config_dir / "shell_history"
    shell_history_dir.mkdir(exist_ok=True)

    # Create empty files
    config_file = config_dir / "config.json"
    history_file = config_dir / "history.json"

    with (
        patch.object(ConfigManager, "CONFIG_DIR", config_dir),
        patch.object(ConfigManager, "CONFIG_FILE", config_file),
        patch.object(ConfigManager, "HISTORY_FILE", history_file),
    ):
        yield {
            "dir": config_dir,
            "config_file": config_file,
            "history_file": history_file,
            "shell_history_dir": shell_history_dir,
        }


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for command execution testing."""
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_os_environ():
    """Provide a consistent mock for os.environ."""
    env = {
        "USER": "testuser",
        "HOME": "/home/testuser",
        "SHELL": "/bin/bash",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
    }

    with patch.dict("os.environ", env, clear=True):
        yield env
