"""
Configuration Management for SmartTerminal.

This module handles loading, saving, and updating configuration settings,
as well as managing command history for context-aware AI interactions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Setup logging
logger = logging.getLogger("smartterminal.config")


class ConfigError(Exception):
    """Exception raised for configuration errors."""

    pass


class ConfigManager:
    """
    Manages configuration settings for SmartTerminal.

    This class handles loading, saving, and updating configuration settings,
    and provides default values when settings are not available.
    """

    # Configuration paths
    CONFIG_DIR = Path.home() / ".smartterminal"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    HISTORY_FILE = CONFIG_DIR / "history.json"

    # Default configuration settings
    DEFAULT_CONFIG = {
        "api_key": "",
        "base_url": "https://api.groq.com/openai/v1",
        "model_name": "llama-3.3-70b-versatile",
        "default_os": "macos",
        "history_limit": 20,
        "log_level": "INFO",
    }

    @classmethod
    def init_config(cls) -> None:
        """
        Initialize configuration directories and files.

        Creates the configuration directory and files if they don't exist.
        If the config file doesn't exist, it creates it with default settings.

        Raises:
            ConfigError: If there's an error creating configuration files.
        """
        try:
            cls.CONFIG_DIR.mkdir(exist_ok=True)

            # Create config file if it doesn't exist
            if not cls.CONFIG_FILE.exists():
                with open(cls.CONFIG_FILE, "w") as f:
                    json.dump(cls.DEFAULT_CONFIG, f, indent=2)
                logger.info(f"Created default config at {cls.CONFIG_FILE}")

            # Create history file if it doesn't exist
            if not cls.HISTORY_FILE.exists():
                with open(cls.HISTORY_FILE, "w") as f:
                    json.dump([], f)
                logger.info(f"Created history file at {cls.HISTORY_FILE}")

        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            raise ConfigError(f"Failed to initialize configuration: {e}")

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Dict[str, Any]: Configuration settings as a dictionary.

        Raises:
            ConfigError: If there's an error loading the configuration.
        """
        try:
            with open(cls.CONFIG_FILE, "r") as f:
                config = json.load(f)

            return config
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Error loading config, using defaults: {e}")
            return cls.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}")
            raise ConfigError(f"Failed to load configuration: {e}")

    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> None:
        """
        Save configuration to file.

        Args:
            config (Dict[str, Any]): Configuration settings to save.

        Raises:
            ConfigError: If there's an error saving the configuration.
        """
        try:
            with open(cls.CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
            logger.debug("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigError(f"Failed to save configuration: {e}")

    @classmethod
    def load_history(cls) -> List[Dict[str, Any]]:
        """
        Load chat history from file.

        Returns:
            List[Dict[str, Any]]: Chat history as a list of message objects.
        """
        try:
            with open(cls.HISTORY_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.debug("History file not found or invalid, returning empty history")
            return []
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    @classmethod
    def save_history(cls, history: List[Dict[str, Any]]) -> None:
        """
        Save chat history to file, limited to configured size.

        Args:
            history (List[Dict[str, Any]]): Chat history to save.
        """
        try:
            config = cls.load_config()
            # Limit history to configured size
            if len(history) > config["history_limit"]:
                history = history[-config["history_limit"] :]

            with open(cls.HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
            logger.debug(f"History saved with {len(history)} entries")
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            # Don't raise an exception for history saving failures
            # as it's not critical to the operation

    @classmethod
    def reset_history(cls) -> None:
        """Clear all command history."""
        try:
            with open(cls.HISTORY_FILE, "w") as f:
                json.dump([], f)
            logger.info("Command history cleared")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            raise ConfigError(f"Failed to clear history: {e}")

    @classmethod
    def update_config_value(cls, key: str, value: Any) -> None:
        """
        Update a single configuration value.

        Args:
            key (str): Configuration key to update.
            value (Any): New value for the key.

        Raises:
            ConfigError: If there's an error updating the configuration.
        """
        try:
            config = cls.load_config()
            config[key] = value
            cls.save_config(config)
            logger.debug(f"Updated config: {key}={value}")
        except Exception as e:
            logger.error(f"Failed to update config value: {e}")
            raise ConfigError(f"Failed to update configuration: {e}")

    @classmethod
    def get_config_value(cls, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value with fallback to default.

        Args:
            key (str): Configuration key to retrieve.
            default (Optional[Any]): Default value if key is not found.

        Returns:
            Any: The configuration value or default.
        """
        try:
            config = cls.load_config()
            return config.get(key, default)
        except Exception as e:
            logger.error(f"Error retrieving config value: {e}")
            return default
