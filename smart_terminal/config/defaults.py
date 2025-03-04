"""
Default configuration settings for SmartTerminal.

This module provides default configuration values and functions to
generate default configurations based on the environment.
"""

import os
import platform
from typing import Dict, Any

# Basic default configuration
DEFAULT_CONFIG = {
    # General settings
    "default_os": "macos"
    if platform.system() == "Darwin"
    else "windows"
    if platform.system() == "Windows"
    else "linux",
    "log_level": "INFO",
    # AI settings
    "api_key": "",
    "base_url": "https://api.groq.com/openai/v1",
    "model_name": "llama-3.3-70b-versatile",
    "temperature": 0.0,
    # History settings
    "history_limit": 20,
    "save_history": True,
    # Shell settings
    "shell_integration_enabled": False,
    "auto_source_commands": False,
}


def get_default_config() -> Dict[str, Any]:
    """
    Get a copy of the default configuration, with environment-specific adjustments.

    This function returns a copy of the default configuration, with any
    environment-specific adjustments applied.

    Returns:
        Dict[str, Any]: Default configuration dictionary
    """
    # Start with a copy of the basic defaults
    config = DEFAULT_CONFIG.copy()

    # Check for environment variables
    if os.environ.get("SMARTTERMINAL_API_KEY"):
        config["api_key"] = os.environ["SMARTTERMINAL_API_KEY"]

    if os.environ.get("SMARTTERMINAL_BASE_URL"):
        config["base_url"] = os.environ["SMARTTERMINAL_BASE_URL"]

    if os.environ.get("SMARTTERMINAL_MODEL"):
        config["model_name"] = os.environ["SMARTTERMINAL_MODEL"]

    if os.environ.get("SMARTTERMINAL_LOG_LEVEL"):
        config["log_level"] = os.environ["SMARTTERMINAL_LOG_LEVEL"]

    # Platform-specific adjustments
    if platform.system() == "Darwin":  # macOS
        # Check if zsh is the default shell
        if "zsh" in os.environ.get("SHELL", ""):
            config["default_shell"] = "zsh"
        else:
            config["default_shell"] = "bash"
    elif platform.system() == "Windows":
        config["default_shell"] = "powershell"
    else:  # Linux and others
        config["default_shell"] = "bash"

    return config


def reset_to_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reset a configuration dictionary to default values.

    This function takes a configuration dictionary and resets all keys
    to their default values, preserving any keys that are not in the defaults.

    Args:
        config: Configuration dictionary to reset

    Returns:
        Dict[str, Any]: Reset configuration dictionary
    """
    defaults = get_default_config()

    # Reset only the keys that exist in defaults
    for key in defaults:
        config[key] = defaults[key]

    return config


def merge_with_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge a configuration dictionary with default values.

    This function takes a configuration dictionary and fills in any missing
    keys with their default values.

    Args:
        config: Configuration dictionary to merge

    Returns:
        Dict[str, Any]: Merged configuration dictionary
    """
    defaults = get_default_config()

    # Start with defaults and update with provided config
    result = defaults.copy()
    result.update(config)

    return result
