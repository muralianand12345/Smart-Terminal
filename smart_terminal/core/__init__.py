"""
Core functionality for SmartTerminal.

This package contains the core components of SmartTerminal,
including the main terminal class, command processing,
and AI integration.
"""

from smart_terminal.core.ai import AIClient
from smart_terminal.core.terminal import SmartTerminal
from smart_terminal.core.context import ContextGenerator
from smart_terminal.core.commands import CommandGenerator, CommandExecutor
from smart_terminal.core.base import AIProvider, CommandProcessor, ShellIntegrator

__all__ = [
    "SmartTerminal",
    "CommandGenerator",
    "CommandExecutor",
    "AIClient",
    "ContextGenerator",
    "AIProvider",
    "CommandProcessor",
    "ShellIntegrator",
]
