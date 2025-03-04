"""
Configuration manager for SmartTerminal.

This module handles loading, saving, and updating configuration settings,
as well as managing command history for context-aware AI interactions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, cast

from smart_terminal.config.defaults import get_default_config, merge_with_defaults
from smart_terminal.exceptions import ConfigError

# Import models
try:
    from smart_terminal.models.config import Config
    from smart_terminal.models.message import Message

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)


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
            # Create config directory
            cls.CONFIG_DIR.mkdir(exist_ok=True)

            # Create config file if it doesn't exist
            if not cls.CONFIG_FILE.exists():
                with open(cls.CONFIG_FILE, "w") as f:
                    json.dump(get_default_config(), f, indent=2)
                logger.info(f"Created default config at {cls.CONFIG_FILE}")

            # Create history file if it doesn't exist
            if not cls.HISTORY_FILE.exists():
                with open(cls.HISTORY_FILE, "w") as f:
                    json.dump([], f)
                logger.info(f"Created history file at {cls.HISTORY_FILE}")

        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            raise ConfigError(
                f"Failed to initialize configuration: {e}",
                config_file=str(cls.CONFIG_FILE),
                cause=e,
            )

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
            # Make sure config directory exists
            cls.CONFIG_DIR.mkdir(exist_ok=True)

            # Check if config file exists
            if not cls.CONFIG_FILE.exists():
                # Create default config
                default_config = get_default_config()
                cls.save_config(default_config)
                return default_config

            # Load config from file
            with open(cls.CONFIG_FILE, "r") as f:
                config = json.load(f)

            # Merge with defaults to ensure all required keys are present
            return merge_with_defaults(config)

        except json.JSONDecodeError as e:
            logger.warning(f"Error decoding config file: {e}")
            logger.warning("Using default configuration")

            # Backup the corrupt file
            if cls.CONFIG_FILE.exists():
                backup_file = cls.CONFIG_FILE.with_suffix(".json.bak")
                cls.CONFIG_FILE.rename(backup_file)
                logger.info(f"Backed up corrupt config file to {backup_file}")

            # Create new default config
            default_config = get_default_config()
            cls.save_config(default_config)

            return default_config

        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}")
            raise ConfigError(
                f"Failed to load configuration: {e}",
                config_file=str(cls.CONFIG_FILE),
                cause=e,
            )

    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration settings to save.

        Raises:
            ConfigError: If there's an error saving the configuration.
        """
        try:
            # Make sure config directory exists
            cls.CONFIG_DIR.mkdir(exist_ok=True)

            # Convert to dict if it's a model
            if MODELS_AVAILABLE and isinstance(config, Config):
                config_dict = config.to_dict()
            else:
                config_dict = config

            # Save to file
            with open(cls.CONFIG_FILE, "w") as f:
                json.dump(config_dict, f, indent=2)

            logger.debug("Configuration saved successfully")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigError(
                f"Failed to save configuration: {e}",
                config_file=str(cls.CONFIG_FILE),
                cause=e,
            )

    @classmethod
    def load_history(cls) -> List[Dict[str, Any]]:
        """
        Load chat history from file.

        Returns:
            List[Dict[str, Any]]: Chat history as a list of message objects.
        """
        try:
            # Check if history file exists
            if not cls.HISTORY_FILE.exists():
                return []

            # Load history from file
            with open(cls.HISTORY_FILE, "r") as f:
                history = json.load(f)

            return history

        except json.JSONDecodeError:
            logger.debug("History file not found or invalid, returning empty history")
            return []

        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    @classmethod
    def save_history(
        cls, history: Union[List[Dict[str, Any]], "List[Message]"]
    ) -> None:
        """
        Save chat history to file, limited to configured size.

        Args:
            history: Chat history to save.
        """
        try:
            # Load config to get history limit
            config = cls.load_config()
            history_limit = config.get("history_limit", 20)

            # Make sure config directory exists
            cls.CONFIG_DIR.mkdir(exist_ok=True)

            # Convert Message objects to dictionaries if needed
            if MODELS_AVAILABLE and history and isinstance(history[0], Message):
                # This is a List[Message], convert to List[Dict]
                history_dicts = []
                for message in history:
                    history_dicts.append(message.to_dict())
            else:
                # Already a List[Dict]
                history_dicts = cast(List[Dict[str, Any]], history)

            # Limit history to configured size
            if len(history_dicts) > history_limit:
                history_dicts = history_dicts[-history_limit:]

            # Save to file
            with open(cls.HISTORY_FILE, "w") as f:
                json.dump(history_dicts, f, indent=2)

            logger.debug(f"History saved with {len(history_dicts)} entries")

        except Exception as e:
            logger.error(f"Error saving history: {e}")
            # Don't raise an exception for history saving failures
            # as it's not critical to the operation

    @classmethod
    def reset_history(cls) -> None:
        """
        Clear all command history.

        Raises:
            ConfigError: If there's an error clearing the history.
        """
        try:
            with open(cls.HISTORY_FILE, "w") as f:
                json.dump([], f)

            logger.info("Command history cleared")

        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            raise ConfigError(
                f"Failed to clear history: {e}",
                config_file=str(cls.HISTORY_FILE),
                cause=e,
            )

    @classmethod
    def update_config_value(cls, key: str, value: Any) -> None:
        """
        Update a single configuration value.

        Args:
            key: Configuration key to update.
            value: New value for the key.

        Raises:
            ConfigError: If there's an error updating the configuration.
        """
        try:
            # Load current config
            config = cls.load_config()

            # Update value
            config[key] = value

            # Save updated config
            cls.save_config(config)

            logger.debug(f"Updated config: {key}={value}")

        except Exception as e:
            logger.error(f"Failed to update config value: {e}")
            raise ConfigError(
                f"Failed to update configuration: {e}", config_key=key, cause=e
            )

    @classmethod
    def get_config_value(cls, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value with fallback to default.

        Args:
            key: Configuration key to retrieve.
            default: Default value if key is not found.

        Returns:
            Any: The configuration value or default.
        """
        try:
            # Load config
            config = cls.load_config()

            # Get value or default
            return config.get(key, default)

        except Exception as e:
            logger.error(f"Error retrieving config value: {e}")
            return default

    @classmethod
    def get_config_model(cls) -> Optional["Config"]:
        """
        Get configuration as a Config model instance.

        Returns:
            Optional[Config]: Config model instance or None if models are not available.
        """
        if not MODELS_AVAILABLE:
            logger.warning("Models not available, returning None for config model")
            return None

        try:
            # Load config
            config_dict = cls.load_config()

            # Convert to Config model
            from smart_terminal.models.config import Config

            return Config.from_dict(config_dict)

        except Exception as e:
            logger.error(f"Error creating config model: {e}")
            return None

    @classmethod
    def save_config_model(cls, config: "Config") -> None:
        """
        Save a Config model instance to file.

        Args:
            config: Config model instance to save.

        Raises:
            ConfigError: If there's an error saving the configuration.
        """
        if not MODELS_AVAILABLE:
            raise ConfigError("Models not available, cannot save config model")

        try:
            # Convert to dict and save
            config_dict = config.to_dict()
            cls.save_config(config_dict)

        except Exception as e:
            logger.error(f"Error saving config model: {e}")
            raise ConfigError(f"Failed to save configuration model: {e}", cause=e)

    @classmethod
    def get_data_dir(cls) -> Path:
        """
        Get the data directory path.

        Returns:
            Path: Data directory path
        """
        data_dir = cls.CONFIG_DIR / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir

    @classmethod
    def get_logs_dir(cls) -> Path:
        """
        Get the logs directory path.

        Returns:
            Path: Logs directory path
        """
        logs_dir = cls.CONFIG_DIR / "logs"
        logs_dir.mkdir(exist_ok=True)
        return logs_dir

    @classmethod
    def get_shell_history_dir(cls) -> Path:
        """
        Get the shell history directory path.

        Returns:
            Path: Shell history directory path
        """
        shell_history_dir = cls.CONFIG_DIR / "shell_history"
        shell_history_dir.mkdir(exist_ok=True)
        return shell_history_dir
