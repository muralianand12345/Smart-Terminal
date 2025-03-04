"""
Configuration management for SmartTerminal.

This package provides tools for loading, saving, and managing application
configuration settings and user preferences.
"""

from smart_terminal.config.manager import ConfigManager
from smart_terminal.config.defaults import DEFAULT_CONFIG, get_default_config

__all__ = ["ConfigManager", "DEFAULT_CONFIG", "get_default_config"]
