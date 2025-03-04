"""
SmartTerminal: AI-Powered Terminal Command Generator and Executor

This package provides a CLI tool that converts natural language instructions into
executable terminal commands. It uses AI to generate appropriate commands with
placeholders for user input.

Features:
- Convert natural language to terminal commands
- Handle multi-step tasks with sequential commands
- Collect user input for command parameters
- Support for different operating systems
- Interactive mode for continuous command generation
- Command history for context-aware interactions
- Proper handling of administrative privileges

Author: Murali Anand (https://github.com/muralianand12345)
"""

__version__ = "1.1.1"

from smart_terminal.terminal import SmartTerminal
from smart_terminal.config import ConfigManager
from smart_terminal.ai import AIClient, AIError
from smart_terminal.commands import CommandGenerator, CommandExecutor, CommandError


__all__ = [
    "SmartTerminal",
    "ConfigManager",
    "AIClient",
    "AIError",
    "CommandGenerator",
    "CommandExecutor",
    "CommandError",
]
