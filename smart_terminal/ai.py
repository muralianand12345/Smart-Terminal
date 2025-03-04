"""
AI Integration Module for SmartTerminal.

This module handles interactions with AI services to convert natural language
into executable terminal commands.
"""

import logging
from typing import List, Iterable, Any, Optional, Dict

# Setup logging
logger = logging.getLogger("smartterminal.ai")

# Try import required packages
try:
    from openai import AsyncOpenAI, OpenAI
    from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
    from openai.types.chat.chat_completion_message_param import (
        ChatCompletionMessageParam,
    )
    from pydantic import BaseModel, Field, ConfigDict
except ImportError as e:
    logger.error(f"Required packages not found: {e}")
    raise ImportError(
        "Required packages not found. Please install 'openai' and 'pydantic' using 'pip install openai pydantic'"
    ) from e


class AIError(Exception):
    """Exception raised for AI interaction errors."""

    pass


class Message(BaseModel):
    """Message model for chat interactions."""

    role: str = Field(..., description="The role of the message")
    content: str = Field(..., description="The content of the message")
    model_config = ConfigDict(protected_namespaces=())


class Tools(BaseModel):
    """Tools model for AI function calls."""

    tools: List[str] = Field(..., description="The tools to use")
    model_config = ConfigDict(protected_namespaces=())


class AIClient:
    """
    Client for AI API interactions.

    This class provides methods for making API calls to AI providers
    to convert natural language into executable commands.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize AI client with API credentials and settings.

        Args:
            api_key (Optional[str]): API key for authentication.
            base_url (Optional[str]): Base URL for API calls.
            model_name (Optional[str]): AI model name to use.

        Raises:
            AIError: If the client initialization fails.
        """
        self.base_url = base_url or "https://api.groq.com/openai/v1"
        self.model_name = model_name or "llama-3.3-70b-versatile"
        self.api_key = api_key

        # Initialize clients
        try:
            self.sync_client = OpenAI(api_key=api_key, base_url=self.base_url)
            self.async_client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)
            logger.debug(f"AI client initialized with model {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
            raise AIError(f"Failed to initialize AI client: {e}")

    @staticmethod
    def create_tool_spec(
        name: str, description: str, parameters: dict, **kwargs
    ) -> Dict[str, Any]:
        """
        Create a tool specification for function calling.

        Args:
            name (str): Tool name.
            description (str): Tool description.
            parameters (dict): JSON schema for parameters.
            **kwargs: Additional tool properties.

        Returns:
            Dict[str, Any]: Tool specification.
        """
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
                "strict": True,
                **kwargs,
            },
        }

    async def invoke_tool_async(
        self,
        tools: Iterable[ChatCompletionToolParam],
        messages: Iterable[ChatCompletionMessageParam],
        **kwargs,
    ) -> Any:
        """
        Invoke tool asynchronously via AI API.

        Args:
            tools: Tool specifications.
            messages: Chat messages.
            **kwargs: Additional API parameters.

        Returns:
            Tool call objects from the API response.

        Raises:
            AIError: If the API call fails.
        """
        try:
            logger.debug(f"Invoking AI with {len(list(messages))} messages")

            # Set default parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "tools": tools,
                "temperature": 0.0,
                "tool_choice": "auto",
            }

            # Update with any additional parameters
            params.update(kwargs)

            # Make the API call
            tools_response = await self.async_client.chat.completions.create(**params)

            # Check for valid response
            if (
                not tools_response.choices
                or not tools_response.choices[0].message.tool_calls
            ):
                logger.warning("AI returned no tool calls")
                return []

            return tools_response.choices[0].message.tool_calls

        except Exception as e:
            logger.error(f"AI tool invocation failed: {e}")
            raise AIError(f"Error communicating with AI service: {e}")

    def invoke_tool_sync(
        self,
        tools: Iterable[ChatCompletionToolParam],
        messages: Iterable[ChatCompletionMessageParam],
        **kwargs,
    ) -> Any:
        """
        Invoke tool synchronously via AI API.

        Args:
            tools: Tool specifications.
            messages: Chat messages.
            **kwargs: Additional API parameters.

        Returns:
            Tool call objects from the API response.

        Raises:
            AIError: If the API call fails.
        """
        try:
            logger.debug(
                f"Invoking AI synchronously with {len(list(messages))} messages"
            )

            # Set default parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "tools": tools,
                "temperature": 0.0,
                "tool_choice": "auto",
            }

            # Update with any additional parameters
            params.update(kwargs)

            # Make the API call
            tools_response = self.sync_client.chat.completions.create(**params)

            # Check for valid response
            if (
                not tools_response.choices
                or not tools_response.choices[0].message.tool_calls
            ):
                logger.warning("AI returned no tool calls")
                return []

            return tools_response.choices[0].message.tool_calls

        except Exception as e:
            logger.error(f"Synchronous AI tool invocation failed: {e}")
            raise AIError(f"Error communicating with AI service: {e}")
