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

__version__ = "2.0.0"

# Import subpackages for easier access
from smart_terminal.models import (
    Command,
    CommandResult,
    AIMessage,
    UserMessage,
    Config,
    ContextData,
)

from smart_terminal.core import (
    SmartTerminal,
    AIClient,
    CommandGenerator,
    CommandExecutor,
)

from smart_terminal.exceptions import (
    SmartTerminalError,
    AIError,
    CommandError,
    ConfigError,
)

# Export primary classes for easier imports
__all__ = [
    # Core components
    "SmartTerminal",
    "AIClient",
    "CommandGenerator",
    "CommandExecutor",
    # Models
    "Command",
    "CommandResult",
    "AIMessage",
    "UserMessage",
    "Config",
    "ContextData",
    # Exceptions
    "SmartTerminalError",
    "AIError",
    "CommandError",
    "ConfigError",
]
