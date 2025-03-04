"""
AI Provider Adapters for SmartTerminal.

This module provides adapter interfaces and implementations for
various AI providers such as OpenAI, Groq, and Anthropic.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from smart_terminal.models.command import ToolCall
from smart_terminal.models.config import AISettings
from smart_terminal.models.message import Message, SystemMessage

# Setup logging
logger = logging.getLogger(__name__)


class AIProviderAdapter(ABC):
    """
    Abstract adapter interface for AI providers.

    This class defines the interface that all AI provider adapters must
    implement, allowing the application to switch between different
    providers without changing its code.
    """

    @abstractmethod
    async def generate_commands(
        self, messages: List[Message], system_prompt: Optional[str] = None
    ) -> List[ToolCall]:
        """
        Generate commands from a list of chat messages.

        Args:
            messages: List of chat messages
            system_prompt: Optional system prompt to override the default

        Returns:
            List of tool calls containing commands

        Raises:
            AIProviderError: If there's an error generating commands
        """
        pass

    @abstractmethod
    async def invoke_tool(
        self,
        messages: List[Message],
        tool_spec: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> List[ToolCall]:
        """
        Invoke a specific tool with the AI provider.

        Args:
            messages: List of chat messages
            tool_spec: Tool specification
            system_prompt: Optional system prompt to override the default

        Returns:
            List of tool calls

        Raises:
            AIProviderError: If there's an error invoking the tool
        """
        pass

    @abstractmethod
    def get_command_tool_spec(self) -> Dict[str, Any]:
        """
        Get the command generation tool specification.

        Returns:
            Tool specification for command generation
        """
        pass

    @classmethod
    @abstractmethod
    def from_settings(cls, settings: AISettings) -> "AIProviderAdapter":
        """
        Create an instance from AI settings.

        Args:
            settings: AI settings

        Returns:
            AIProviderAdapter instance
        """
        pass


class AIProviderError(Exception):
    """Exception raised for AI provider errors."""

    pass


class OpenAIAdapter(AIProviderAdapter):
    """
    Adapter for OpenAI API.

    This adapter implements the AIProviderAdapter interface for
    OpenAI's API, handling the details of API communication.
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
    ):
        """
        Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key
            base_url: Optional base URL for API requests
            model_name: Model name to use
            temperature: Temperature parameter for generation
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model_name = model_name
        self.temperature = temperature

        try:
            from openai import AsyncOpenAI

            # Initialize clients
            self.async_client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)

            logger.debug(f"OpenAI adapter initialized with model {self.model_name}")
        except ImportError:
            logger.error("OpenAI Python package not installed")
            raise AIProviderError(
                "OpenAI Python package not installed. "
                "Please install with 'pip install openai'"
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise AIProviderError(f"Failed to initialize OpenAI client: {e}")

    def get_command_tool_spec(self) -> Dict[str, Any]:
        """
        Get the command generation tool specification.

        Returns:
            Tool specification for command generation
        """
        return {
            "type": "function",
            "function": {
                "name": "get_command",
                "description": "Get a single terminal command to execute. For tasks requiring multiple commands, this tool should be called multiple times in sequence.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "A single terminal command with placeholders for user inputs enclosed in angle brackets (e.g., 'mkdir <folder_name>')",
                        },
                        "user_inputs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of input values that the user needs to provide to execute the command. These correspond to the placeholders in the command string.",
                        },
                        "os": {
                            "type": "string",
                            "enum": ["macos", "linux", "windows"],
                            "description": "The operating system for which this command is intended",
                            "default": "macos",
                        },
                        "requires_admin": {
                            "type": "boolean",
                            "description": "Whether this command requires administrator or root privileges",
                            "default": False,
                        },
                        "description": {
                            "type": "string",
                            "description": "A brief description of what this command does",
                        },
                    },
                    "required": ["command", "user_inputs"],
                    "additionalProperties": False,
                },
            },
        }

    async def generate_commands(
        self, messages: List[Message], system_prompt: Optional[str] = None
    ) -> List[ToolCall]:
        """
        Generate commands from a list of chat messages.

        Args:
            messages: List of chat messages
            system_prompt: Optional system prompt to override the default

        Returns:
            List of tool calls containing commands

        Raises:
            AIProviderError: If there's an error generating commands
        """
        # Create a copy of messages to avoid modifying the original
        messages_copy = messages.copy()

        # Add or replace system message if provided
        if system_prompt:
            for i, message in enumerate(messages_copy):
                if message.role == "system":
                    messages_copy[i] = SystemMessage(
                        role="system", content=system_prompt
                    )
                    break
            else:
                messages_copy.insert(
                    0, SystemMessage(role="system", content=system_prompt)
                )

        # Convert messages to OpenAI format
        api_messages = [message.to_dict() for message in messages_copy]

        # Get command tool spec
        tools = [self.get_command_tool_spec()]

        try:
            logger.debug(f"Generating commands with {len(messages_copy)} messages")

            # Make API call
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=api_messages,
                tools=tools,
                temperature=self.temperature,
                tool_choice="auto",
            )

            # Check for valid response
            if not response.choices or not response.choices[0].message.tool_calls:
                logger.warning("No tool calls returned from OpenAI")
                return []

            # Convert to ToolCall objects
            tool_calls = []
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        type=tc.type,
                        function_name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

            return tool_calls

        except Exception as e:
            logger.error(f"Error generating commands with OpenAI: {e}")
            raise AIProviderError(f"Error generating commands: {e}")

    async def invoke_tool(
        self,
        messages: List[Message],
        tool_spec: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> List[ToolCall]:
        """
        Invoke a specific tool with the AI provider.

        Args:
            messages: List of chat messages
            tool_spec: Tool specification
            system_prompt: Optional system prompt to override the default

        Returns:
            List of tool calls

        Raises:
            AIProviderError: If there's an error invoking the tool
        """
        # Create a copy of messages to avoid modifying the original
        messages_copy = messages.copy()

        # Add or replace system message if provided
        if system_prompt:
            for i, message in enumerate(messages_copy):
                if message.role == "system":
                    messages_copy[i] = SystemMessage(
                        role="system", content=system_prompt
                    )
                    break
            else:
                messages_copy.insert(
                    0, SystemMessage(role="system", content=system_prompt)
                )

        # Convert messages to OpenAI format
        api_messages = [message.to_dict() for message in messages_copy]

        try:
            logger.debug(f"Invoking tool with {len(messages_copy)} messages")

            # Make API call
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=api_messages,
                tools=[tool_spec],
                temperature=self.temperature,
                tool_choice={
                    "type": "function",
                    "function": {"name": tool_spec["function"]["name"]},
                },
            )

            # Check for valid response
            if not response.choices or not response.choices[0].message.tool_calls:
                logger.warning("No tool calls returned from OpenAI")
                return []

            # Convert to ToolCall objects
            tool_calls = []
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        type=tc.type,
                        function_name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

            return tool_calls

        except Exception as e:
            logger.error(f"Error invoking tool with OpenAI: {e}")
            raise AIProviderError(f"Error invoking tool: {e}")

    @classmethod
    def from_settings(cls, settings: AISettings) -> "OpenAIAdapter":
        """
        Create an instance from AI settings.

        Args:
            settings: AI settings

        Returns:
            OpenAIAdapter instance
        """
        return cls(
            api_key=settings.api_key,
            base_url=settings.base_url,
            model_name=settings.model_name,
            temperature=settings.temperature,
        )


class GroqAdapter(AIProviderAdapter):
    """
    Adapter for Groq API.

    This adapter implements the AIProviderAdapter interface for
    Groq's API, which is compatible with the OpenAI API format
    but uses different model names and base URL.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "llama-3.1-70b-versatile",
        temperature: float = 0.0,
    ):
        """
        Initialize Groq adapter.

        Args:
            api_key: Groq API key
            model_name: Model name to use
            temperature: Temperature parameter for generation
        """
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.model_name = model_name
        self.temperature = temperature

        try:
            from openai import AsyncOpenAI

            # Initialize clients
            self.async_client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)

            logger.debug(f"Groq adapter initialized with model {self.model_name}")
        except ImportError:
            logger.error("OpenAI Python package not installed")
            raise AIProviderError(
                "OpenAI Python package not installed. "
                "Please install with 'pip install openai'"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise AIProviderError(f"Failed to initialize Groq client: {e}")

    def get_command_tool_spec(self) -> Dict[str, Any]:
        """
        Get the command generation tool specification.

        Returns:
            Tool specification for command generation
        """
        return {
            "type": "function",
            "function": {
                "name": "get_command",
                "description": "Get a single terminal command to execute. For tasks requiring multiple commands, this tool should be called multiple times in sequence.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "A single terminal command with placeholders for user inputs enclosed in angle brackets (e.g., 'mkdir <folder_name>')",
                        },
                        "user_inputs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of input values that the user needs to provide to execute the command. These correspond to the placeholders in the command string.",
                        },
                        "os": {
                            "type": "string",
                            "enum": ["macos", "linux", "windows"],
                            "description": "The operating system for which this command is intended",
                            "default": "macos",
                        },
                        "requires_admin": {
                            "type": "boolean",
                            "description": "Whether this command requires administrator or root privileges",
                            "default": False,
                        },
                        "description": {
                            "type": "string",
                            "description": "A brief description of what this command does",
                        },
                    },
                    "required": ["command", "user_inputs"],
                    "additionalProperties": False,
                },
            },
        }

    async def generate_commands(
        self, messages: List[Message], system_prompt: Optional[str] = None
    ) -> List[ToolCall]:
        """
        Generate commands from a list of chat messages.

        Args:
            messages: List of chat messages
            system_prompt: Optional system prompt to override the default

        Returns:
            List of tool calls containing commands

        Raises:
            AIProviderError: If there's an error generating commands
        """
        # Create a copy of messages to avoid modifying the original
        messages_copy = messages.copy()

        # Add or replace system message if provided
        if system_prompt:
            for i, message in enumerate(messages_copy):
                if message.role == "system":
                    messages_copy[i] = SystemMessage(
                        role="system", content=system_prompt
                    )
                    break
            else:
                messages_copy.insert(
                    0, SystemMessage(role="system", content=system_prompt)
                )

        # Convert messages to OpenAI format
        api_messages = [message.to_dict() for message in messages_copy]

        # Get command tool spec
        tools = [self.get_command_tool_spec()]

        try:
            logger.debug(f"Generating commands with {len(messages_copy)} messages")

            # Make API call
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=api_messages,
                tools=tools,
                temperature=self.temperature,
                tool_choice="auto",
            )

            # Check for valid response
            if not response.choices or not response.choices[0].message.tool_calls:
                logger.warning("No tool calls returned from Groq")
                return []

            # Convert to ToolCall objects
            tool_calls = []
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        type=tc.type,
                        function_name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

            return tool_calls

        except Exception as e:
            logger.error(f"Error generating commands with Groq: {e}")
            raise AIProviderError(f"Error generating commands: {e}")

    async def invoke_tool(
        self,
        messages: List[Message],
        tool_spec: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> List[ToolCall]:
        """
        Invoke a specific tool with the AI provider.

        Args:
            messages: List of chat messages
            tool_spec: Tool specification
            system_prompt: Optional system prompt to override the default

        Returns:
            List of tool calls

        Raises:
            AIProviderError: If there's an error invoking the tool
        """
        # Create a copy of messages to avoid modifying the original
        messages_copy = messages.copy()

        # Add or replace system message if provided
        if system_prompt:
            for i, message in enumerate(messages_copy):
                if message.role == "system":
                    messages_copy[i] = SystemMessage(
                        role="system", content=system_prompt
                    )
                    break
            else:
                messages_copy.insert(
                    0, SystemMessage(role="system", content=system_prompt)
                )

        # Convert messages to OpenAI format
        api_messages = [message.to_dict() for message in messages_copy]

        try:
            logger.debug(f"Invoking tool with {len(messages_copy)} messages")

            # Make API call
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=api_messages,
                tools=[tool_spec],
                temperature=self.temperature,
                tool_choice={
                    "type": "function",
                    "function": {"name": tool_spec["function"]["name"]},
                },
            )

            # Check for valid response
            if not response.choices or not response.choices[0].message.tool_calls:
                logger.warning("No tool calls returned from Groq")
                return []

            # Convert to ToolCall objects
            tool_calls = []
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        type=tc.type,
                        function_name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

            return tool_calls

        except Exception as e:
            logger.error(f"Error invoking tool with Groq: {e}")
            raise AIProviderError(f"Error invoking tool: {e}")

    @classmethod
    def from_settings(cls, settings: AISettings) -> "GroqAdapter":
        """
        Create an instance from AI settings.

        Args:
            settings: AI settings

        Returns:
            GroqAdapter instance
        """
        return cls(
            api_key=settings.api_key,
            model_name=settings.model_name,
            temperature=settings.temperature,
        )


class AnthropicAdapter(AIProviderAdapter):
    """
    Adapter for Anthropic API.

    This adapter implements the AIProviderAdapter interface for
    Anthropic's API, handling the specific formatting and parameters.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-opus-20240229",
        temperature: float = 0.0,
    ):
        """
        Initialize Anthropic adapter.

        Args:
            api_key: Anthropic API key
            model_name: Model name to use
            temperature: Temperature parameter for generation
        """
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature

        try:
            from anthropic import AsyncAnthropic

            # Initialize client
            self.async_client = AsyncAnthropic(api_key=api_key)

            logger.debug(f"Anthropic adapter initialized with model {self.model_name}")
        except ImportError:
            logger.error("Anthropic Python package not installed")
            raise AIProviderError(
                "Anthropic Python package not installed. "
                "Please install with 'pip install anthropic'"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise AIProviderError(f"Failed to initialize Anthropic client: {e}")

    def get_command_tool_spec(self) -> Dict[str, Any]:
        """
        Get the command generation tool specification.

        Returns:
            Tool specification for command generation
        """
        return {
            "name": "get_command",
            "description": "Get a single terminal command to execute. For tasks requiring multiple commands, this tool should be called multiple times in sequence.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "A single terminal command with placeholders for user inputs enclosed in angle brackets (e.g., 'mkdir <folder_name>')",
                    },
                    "user_inputs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of input values that the user needs to provide to execute the command. These correspond to the placeholders in the command string.",
                    },
                    "os": {
                        "type": "string",
                        "enum": ["macos", "linux", "windows"],
                        "description": "The operating system for which this command is intended",
                        "default": "macos",
                    },
                    "requires_admin": {
                        "type": "boolean",
                        "description": "Whether this command requires administrator or root privileges",
                        "default": False,
                    },
                    "description": {
                        "type": "string",
                        "description": "A brief description of what this command does",
                    },
                },
                "required": ["command", "user_inputs"],
            },
        }

    async def generate_commands(
        self, messages: List[Message], system_prompt: Optional[str] = None
    ) -> List[ToolCall]:
        """
        Generate commands from a list of chat messages.

        Args:
            messages: List of chat messages
            system_prompt: Optional system prompt to override the default

        Returns:
            List of tool calls containing commands

        Raises:
            AIProviderError: If there's an error generating commands
        """
        from anthropic import tools as anthropic_tools

        # Create a copy of messages to avoid modifying the original
        messages_copy = messages.copy()

        # Extract system message if present
        system_message_content = system_prompt
        if not system_message_content:
            for msg in messages_copy:
                if msg.role == "system":
                    system_message_content = msg.content
                    messages_copy.remove(msg)
                    break

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages_copy:
            if msg.role == "user":
                anthropic_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                assistant_msg = {"role": "assistant"}

                # Handle content or tool calls
                if msg.content:
                    assistant_msg["content"] = msg.content

                anthropic_messages.append(assistant_msg)

        # Get command tool spec
        tool_spec = self.get_command_tool_spec()

        try:
            logger.debug(f"Generating commands with {len(messages_copy)} messages")

            # Make API call
            response = await self.async_client.messages.create(
                model=self.model_name,
                messages=anthropic_messages,
                system=system_message_content,
                tools=[anthropic_tools.Tool.from_dict(tool_spec)],
                temperature=self.temperature,
                max_tokens=1024,
            )

            # Check for valid response
            if not response.content or not any(
                block.type == "tool_use" for block in response.content
            ):
                logger.warning("No tool calls returned from Anthropic")
                return []

            # Convert to ToolCall objects
            tool_calls = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_use = content_block.tool_use
                    tool_calls.append(
                        ToolCall(
                            id=tool_use.id,
                            type="function",
                            function_name=tool_use.name,
                            arguments=tool_use.input,
                        )
                    )

            return tool_calls

        except Exception as e:
            logger.error(f"Error generating commands with Anthropic: {e}")
            raise AIProviderError(f"Error generating commands: {e}")

    async def invoke_tool(
        self,
        messages: List[Message],
        tool_spec: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> List[ToolCall]:
        """
        Invoke a specific tool with the AI provider.

        Args:
            messages: List of chat messages
            tool_spec: Tool specification
            system_prompt: Optional system prompt to override the default

        Returns:
            List of tool calls

        Raises:
            AIProviderError: If there's an error invoking the tool
        """
        from anthropic import tools as anthropic_tools

        # Create a copy of messages to avoid modifying the original
        messages_copy = messages.copy()

        # Extract system message if present
        system_message_content = system_prompt
        if not system_message_content:
            for msg in messages_copy:
                if msg.role == "system":
                    system_message_content = msg.content
                    messages_copy.remove(msg)
                    break

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages_copy:
            if msg.role == "user":
                anthropic_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                assistant_msg = {"role": "assistant"}

                # Handle content or tool calls
                if msg.content:
                    assistant_msg["content"] = msg.content

                anthropic_messages.append(assistant_msg)

        # Convert OpenAI-style tool spec to Anthropic format
        anthropic_tool_spec = {
            "name": tool_spec["function"]["name"],
            "description": tool_spec["function"]["description"],
            "input_schema": tool_spec["function"]["parameters"],
        }

        try:
            logger.debug(f"Invoking tool with {len(messages_copy)} messages")

            # Make API call
            response = await self.async_client.messages.create(
                model=self.model_name,
                messages=anthropic_messages,
                system=system_message_content,
                tools=[anthropic_tools.Tool.from_dict(anthropic_tool_spec)],
                temperature=self.temperature,
                max_tokens=1024,
            )

            # Check for valid response
            if not response.content or not any(
                block.type == "tool_use" for block in response.content
            ):
                logger.warning("No tool calls returned from Anthropic")
                return []

            # Convert to ToolCall objects
            tool_calls = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_use = content_block.tool_use
                    tool_calls.append(
                        ToolCall(
                            id=tool_use.id,
                            type="function",
                            function_name=tool_use.name,
                            arguments=tool_use.input,
                        )
                    )

            return tool_calls

        except Exception as e:
            logger.error(f"Error invoking tool with Anthropic: {e}")
            raise AIProviderError(f"Error invoking tool: {e}")

    @classmethod
    def from_settings(cls, settings: AISettings) -> "AnthropicAdapter":
        """
        Create an instance from AI settings.

        Args:
            settings: AI settings

        Returns:
            AnthropicAdapter instance
        """
        return cls(
            api_key=settings.api_key,
            model_name=settings.model_name,
            temperature=settings.temperature,
        )


class AIProviderFactory:
    """
    Factory for creating AI provider adapter instances.

    This class provides methods for creating AI provider adapter instances
    based on the provider name and settings.
    """

    PROVIDERS = {
        "openai": OpenAIAdapter,
        "groq": GroqAdapter,
        "anthropic": AnthropicAdapter,
    }

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: str,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
    ) -> AIProviderAdapter:
        """
        Create an AI provider adapter instance.

        Args:
            provider: Provider name (openai, groq, anthropic)
            api_key: API key
            base_url: Optional base URL for API requests
            model_name: Optional model name
            temperature: Temperature parameter for generation

        Returns:
            AIProviderAdapter instance

        Raises:
            ValueError: If the provider is not supported
        """
        provider = provider.lower()

        if provider not in cls.PROVIDERS:
            raise ValueError(
                f"Unsupported AI provider: {provider}. Supported providers: {', '.join(cls.PROVIDERS.keys())}"
            )

        provider_class = cls.PROVIDERS[provider]

        kwargs = {"api_key": api_key, "temperature": temperature}

        if model_name:
            kwargs["model_name"] = model_name

        # Only OpenAI adapter supports base_url
        if base_url and provider == "openai":
            kwargs["base_url"] = base_url

        return provider_class(**kwargs)
