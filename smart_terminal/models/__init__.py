"""
Data models for SmartTerminal.

This module provides Pydantic models for representing various data structures
used throughout the application, ensuring type safety and validation.
"""

from smart_terminal.models.config import Config, HistorySettings
from smart_terminal.models.command import Command, CommandResult, ToolCall
from smart_terminal.models.message import Message, UserMessage, AIMessage, SystemMessage
from smart_terminal.models.context import (
    ContextData,
    DirectoryInfo,
    SystemInfo,
    GitInfo,
)

__all__ = [
    # Command models
    "Command",
    "CommandResult",
    "ToolCall",
    # Message models
    "Message",
    "UserMessage",
    "AIMessage",
    "SystemMessage",
    # Configuration models
    "Config",
    "HistorySettings",
    # Context models
    "ContextData",
    "DirectoryInfo",
    "SystemInfo",
    "GitInfo",
]
