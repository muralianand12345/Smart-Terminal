"""
Tests for the config module.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from smart_terminal.config import ConfigManager, ConfigError


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_init_config(self, tmp_path):
        """Test initializing configuration."""
        config_dir = tmp_path / ".smartterminal"
        config_file = config_dir / "config.json"
        history_file = config_dir / "history.json"

        # Patch the config paths
        with (
            patch.object(ConfigManager, "CONFIG_DIR", config_dir),
            patch.object(ConfigManager, "CONFIG_FILE", config_file),
            patch.object(ConfigManager, "HISTORY_FILE", history_file),
        ):
            ConfigManager.init_config()

            # Check that the directory and files were created
            assert config_dir.exists()
            assert config_file.exists()
            assert history_file.exists()

            # Check the config file content
            with open(config_file, "r") as f:
                config = json.load(f)
                assert config["api_key"] == ""
                assert config["base_url"] == "https://api.groq.com/openai/v1"
                assert config["model_name"] == "llama-3.3-70b-versatile"
                assert config["default_os"] == "macos"
                assert config["history_limit"] == 20
                assert config["log_level"] == "INFO"

            # Check the history file content
            with open(history_file, "r") as f:
                history = json.load(f)
                assert history == []

    def test_init_config_error(self):
        """Test error handling in init_config."""
        # Patch mkdir to raise an exception
        with (
            patch(
                "pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")
            ),
            pytest.raises(ConfigError) as excinfo,
        ):
            ConfigManager.init_config()

            assert "Failed to initialize configuration" in str(excinfo.value)

    def test_load_config_success(self, tmp_path):
        """Test successful config loading."""
        # Create a mock config file
        config_data = {"api_key": "test_key", "base_url": "test_url"}
        config_file = tmp_path / "config.json"

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Patch the CONFIG_FILE path to use our temporary file
        with patch.object(ConfigManager, "CONFIG_FILE", config_file):
            config = ConfigManager.load_config()
            assert config["api_key"] == "test_key"
            assert config["base_url"] == "test_url"

    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist."""
        # Patch the CONFIG_FILE to a non-existent path
        with patch.object(ConfigManager, "CONFIG_FILE", Path("/nonexistent/path")):
            config = ConfigManager.load_config()
            # Should return default config
            assert "api_key" in config
            assert config["base_url"] == "https://api.groq.com/openai/v1"

    def test_load_config_json_error(self):
        """Test config loading with invalid JSON."""
        mock_file = mock_open(read_data="invalid json")

        with (
            patch("builtins.open", mock_file),
            patch.object(ConfigManager, "CONFIG_FILE", Path("config.json")),
        ):
            config = ConfigManager.load_config()
            # Should return default config
            assert "api_key" in config
            assert config["base_url"] == "https://api.groq.com/openai/v1"

    def test_load_config_unexpected_error(self):
        """Test unexpected error in load_config."""
        with (
            patch("builtins.open", side_effect=Exception("Unexpected error")),
            patch.object(ConfigManager, "CONFIG_FILE", Path("config.json")),
            pytest.raises(ConfigError) as excinfo,
        ):
            ConfigManager.load_config()
            assert "Failed to load configuration" in str(excinfo.value)

    def test_save_config(self, tmp_path):
        """Test saving configuration."""
        config_file = tmp_path / "config.json"
        config_data = {"api_key": "new_key", "base_url": "new_url"}

        with patch.object(ConfigManager, "CONFIG_FILE", config_file):
            ConfigManager.save_config(config_data)

            # Check that the file was created with the correct content
            with open(config_file, "r") as f:
                saved_config = json.load(f)
                assert saved_config["api_key"] == "new_key"
                assert saved_config["base_url"] == "new_url"

    def test_save_config_error(self):
        """Test error handling in save_config."""
        with (
            patch("builtins.open", side_effect=PermissionError("Permission denied")),
            patch.object(ConfigManager, "CONFIG_FILE", Path("config.json")),
            pytest.raises(ConfigError) as excinfo,
        ):
            ConfigManager.save_config({"api_key": "test"})
            assert "Failed to save configuration" in str(excinfo.value)

    def test_load_history_success(self, tmp_path):
        """Test successful history loading."""
        history_data = [{"role": "user", "content": "test"}]
        history_file = tmp_path / "history.json"

        with open(history_file, "w") as f:
            json.dump(history_data, f)

        with patch.object(ConfigManager, "HISTORY_FILE", history_file):
            history = ConfigManager.load_history()
            assert len(history) == 1
            assert history[0]["role"] == "user"
            assert history[0]["content"] == "test"

    def test_load_history_file_not_found(self):
        """Test history loading when file doesn't exist."""
        with patch.object(ConfigManager, "HISTORY_FILE", Path("/nonexistent/path")):
            history = ConfigManager.load_history()
            assert history == []

    def test_save_history(self, tmp_path):
        """Test saving history with limit enforcement."""
        history_file = tmp_path / "history.json"
        config_file = tmp_path / "config.json"

        # Create a mock config with history_limit
        with open(config_file, "w") as f:
            json.dump({"history_limit": 2}, f)

        with (
            patch.object(ConfigManager, "HISTORY_FILE", history_file),
            patch.object(ConfigManager, "CONFIG_FILE", config_file),
        ):
            # Create history with 3 items (exceeding limit of 2)
            history = [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
                {"role": "user", "content": "third"},
            ]

            ConfigManager.save_history(history)

            # Check that only the last 2 items were saved
            with open(history_file, "r") as f:
                saved_history = json.load(f)
                assert len(saved_history) == 2
                assert saved_history[0]["content"] == "second"
                assert saved_history[1]["content"] == "third"

    def test_reset_history(self, tmp_path):
        """Test resetting history."""
        history_file = tmp_path / "history.json"

        # Create a history file with some data
        with open(history_file, "w") as f:
            json.dump([{"role": "user", "content": "test"}], f)

        with patch.object(ConfigManager, "HISTORY_FILE", history_file):
            ConfigManager.reset_history()

            # Check that the file was reset to an empty array
            with open(history_file, "r") as f:
                history = json.load(f)
                assert history == []

    def test_reset_history_error(self):
        """Test error handling in reset_history."""
        with (
            patch("builtins.open", side_effect=PermissionError("Permission denied")),
            patch.object(ConfigManager, "HISTORY_FILE", Path("history.json")),
            pytest.raises(ConfigError) as excinfo,
        ):
            ConfigManager.reset_history()
            assert "Failed to clear history" in str(excinfo.value)

    def test_update_config_value(self, tmp_path):
        """Test updating a single config value."""
        config_file = tmp_path / "config.json"

        # Create initial config
        with open(config_file, "w") as f:
            json.dump({"api_key": "old_key", "base_url": "old_url"}, f)

        with patch.object(ConfigManager, "CONFIG_FILE", config_file):
            ConfigManager.update_config_value("api_key", "new_key")

            # Check that only the specified value was updated
            with open(config_file, "r") as f:
                config = json.load(f)
                assert config["api_key"] == "new_key"
                assert config["base_url"] == "old_url"

    def test_get_config_value(self, tmp_path):
        """Test getting a config value with default fallback."""
        config_file = tmp_path / "config.json"

        # Create config file
        with open(config_file, "w") as f:
            json.dump({"existing_key": "value"}, f)

        with patch.object(ConfigManager, "CONFIG_FILE", config_file):
            # Test getting existing value
            value = ConfigManager.get_config_value("existing_key")
            assert value == "value"

            # Test getting non-existent value with default
            value = ConfigManager.get_config_value("nonexistent_key", "default_value")
            assert value == "default_value"

            # Test error handling
            with patch("builtins.open", side_effect=Exception("Test error")):
                value = ConfigManager.get_config_value("any_key", "fallback")
                assert value == "fallback"
