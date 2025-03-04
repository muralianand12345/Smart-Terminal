"""
Adapters for external services and APIs used by SmartTerminal.

This package provides adapter interfaces and implementations for
external services and APIs, such as AI providers and shell environments.
"""

from smart_terminal.adapters.ai_provider import (
    AIProviderAdapter,
    OpenAIAdapter,
    GroqAdapter,
    AnthropicAdapter,
    AIProviderFactory,
    AIProviderError,
)

from smart_terminal.adapters.shell import (
    ShellAdapter,
    BashAdapter,
    ZshAdapter,
    PowerShellAdapter,
    ShellAdapterFactory,
)

__all__ = [
    # AI provider adapters
    "AIProviderAdapter",
    "OpenAIAdapter",
    "GroqAdapter",
    "AnthropicAdapter",
    "AIProviderFactory",
    "AIProviderError",
    # Shell adapters
    "ShellAdapter",
    "BashAdapter",
    "ZshAdapter",
    "PowerShellAdapter",
    "ShellAdapterFactory",
]
