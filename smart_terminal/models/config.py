"""
Configuration models for SmartTerminal.

This module defines models for representing application configuration,
including AI settings, history preferences, and other customizable options.
"""

from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator


class LogLevel(str, Enum):
    """Log level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class OsType(str, Enum):
    """Supported operating system types."""

    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"


class HistorySettings(BaseModel):
    """Settings for command history management."""

    history_limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to keep in history",
    )

    save_history: bool = Field(
        default=True, description="Whether to save command history between sessions"
    )


class AISettings(BaseModel):
    """Settings for AI service integration."""

    api_key: str = Field(default="", description="API key for the AI service")

    base_url: str = Field(
        default="https://api.groq.com/openai/v1", description="Base URL for API calls"
    )

    model_name: str = Field(
        default="llama-3.3-70b-versatile",
        description="Model name to use for command generation",
    )

    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature parameter for AI (higher = more creative)",
    )


class ShellSettings(BaseModel):
    """Settings for shell integration."""

    shell_integration_enabled: bool = Field(
        default=False, description="Whether shell integration is enabled"
    )

    auto_source_commands: bool = Field(
        default=False,
        description="Whether to automatically source commands that modify environment",
    )


class CacheSettings(BaseModel):
    """Settings for command caching functionality."""

    cache_enabled: bool = Field(
        default=True, description="Whether command caching is enabled"
    )

    cache_max_entries: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Maximum number of entries to store in cache",
    )

    cache_max_age_days: int = Field(
        default=30, ge=1, le=365, description="Maximum age of cache entries in days"
    )

    cache_min_similarity: float = Field(
        default=0.85,
        ge=0.5,
        le=0.99,
        description="Minimum similarity score for fuzzy matching",
    )

    cache_fuzzy_matching: bool = Field(
        default=True, description="Whether to enable fuzzy matching for queries"
    )


class Config(BaseModel):
    """
    Main configuration model for SmartTerminal.

    This model represents the complete application configuration,
    including all settings categories and provides methods for
    serialization and validation.
    """

    # General settings
    default_os: OsType = Field(
        default=OsType.MACOS,
        description="Default operating system for command generation",
    )

    log_level: LogLevel = Field(
        default=LogLevel.INFO, description="Logging verbosity level"
    )

    # Component-specific settings
    ai: AISettings = Field(
        default_factory=AISettings, description="AI service settings"
    )

    history: HistorySettings = Field(
        default_factory=HistorySettings, description="History management settings"
    )

    shell: ShellSettings = Field(
        default_factory=ShellSettings, description="Shell integration settings"
    )

    cache: CacheSettings = Field(
        default_factory=CacheSettings, description="Command caching settings"
    )

    # Custom settings
    custom: Dict[str, Any] = Field(
        default_factory=dict, description="Custom configuration settings"
    )

    @field_validator("custom")
    @classmethod
    def validate_custom(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that custom settings don't contain protected keys."""
        protected_keys = {"default_os", "log_level", "ai", "history", "shell"}

        for key in protected_keys:
            if key in v:
                raise ValueError(
                    f"Custom settings cannot override protected key: {key}"
                )

        return v

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert config to a flat dictionary for storage.

        Returns:
            Dict[str, Any]: Flattened configuration dictionary
        """
        config_dict = {
            "default_os": self.default_os.value,
            "log_level": self.log_level.value,
            # AI settings
            "api_key": self.ai.api_key,
            "base_url": self.ai.base_url,
            "model_name": self.ai.model_name,
            "temperature": self.ai.temperature,
            # History settings
            "history_limit": self.history.history_limit,
            "save_history": self.history.save_history,
            # Shell settings
            "shell_integration_enabled": self.shell.shell_integration_enabled,
            "auto_source_commands": self.shell.auto_source_commands,
        }

        # Add custom settings
        for key, value in self.custom.items():
            config_dict[key] = value

        return config_dict

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """
        Create a Config instance from a dictionary.

        Args:
            config_dict: Dictionary containing configuration values

        Returns:
            Config instance
        """
        # Extract known settings
        ai_settings = AISettings(
            api_key=config_dict.get("api_key", ""),
            base_url=config_dict.get("base_url", "https://api.groq.com/openai/v1"),
            model_name=config_dict.get("model_name", "llama-3.3-70b-versatile"),
            temperature=config_dict.get("temperature", 0.0),
        )

        history_settings = HistorySettings(
            history_limit=config_dict.get("history_limit", 20),
            save_history=config_dict.get("save_history", True),
        )

        shell_settings = ShellSettings(
            shell_integration_enabled=config_dict.get(
                "shell_integration_enabled", False
            ),
            auto_source_commands=config_dict.get("auto_source_commands", False),
        )

        # Create a set of known keys
        known_keys = {
            "default_os",
            "log_level",
            "api_key",
            "base_url",
            "model_name",
            "temperature",
            "history_limit",
            "save_history",
            "shell_integration_enabled",
            "auto_source_commands",
        }

        # Extract custom settings
        custom_settings = {k: v for k, v in config_dict.items() if k not in known_keys}

        return cls(
            default_os=config_dict.get("default_os", OsType.MACOS),
            log_level=config_dict.get("log_level", LogLevel.INFO),
            ai=ai_settings,
            history=history_settings,
            shell=shell_settings,
            custom=custom_settings,
        )
