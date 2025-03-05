"""
AI Integration Module for SmartTerminal.

This module handles interactions with AI services to convert natural language
into executable terminal commands.
"""

import json
import logging
from typing import List, Dict, Any, Optional

from smart_terminal.exceptions import AIError
from smart_terminal.core.base import AIProvider

# Import models if available
try:
    from smart_terminal.models.config import AISettings
    from smart_terminal.models.command import Command, ToolCall
    from smart_terminal.models.message import (
        Message,
        UserMessage,
        AIMessage,
        SystemMessage,
    )

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)


class AIClient(AIProvider):
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
        temperature: float = 0.0,
    ):
        """
        Initialize AI client with API credentials and settings.

        Args:
            api_key: API key for authentication
            base_url: Base URL for API calls
            model_name: AI model name to use
            temperature: Temperature parameter for generation

        Raises:
            AIError: If the client initialization fails
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.groq.com/openai/v1"
        self.model_name = model_name or "llama-3.3-70b-versatile"
        self.temperature = temperature

        # Try to initialize AI adapter
        try:
            # First try to use the adapter module if available
            try:
                from smart_terminal.adapters.ai_provider import AIProviderFactory

                # Determine provider from base URL
                if "groq.com" in self.base_url.lower():
                    provider = "groq"
                elif "anthropic.com" in self.base_url.lower():
                    provider = "anthropic"
                else:
                    provider = "openai"

                self.adapter = AIProviderFactory.create(
                    provider=provider,
                    api_key=api_key,
                    base_url=self.base_url,
                    model_name=self.model_name,
                    temperature=self.temperature,
                )

                logger.debug(
                    f"Using adapter for {provider} with model {self.model_name}"
                )
                self._using_adapter = True

            except (ImportError, Exception) as e:
                logger.debug(f"Adapter not available, using direct implementation: {e}")
                self._using_adapter = False

                # Initialize OpenAI client
                try:
                    from openai import AsyncOpenAI, OpenAI

                    # Initialize clients
                    self.async_client = AsyncOpenAI(
                        api_key=api_key, base_url=self.base_url
                    )
                    self.sync_client = OpenAI(api_key=api_key, base_url=self.base_url)

                    logger.debug(f"AI client initialized with model {self.model_name}")

                except ImportError:
                    raise AIError(
                        "Required package 'openai' not found. "
                        "Please install using 'pip install openai'"
                    )

        except Exception as e:
            raise AIError(f"Failed to initialize AI client: {e}")

    def get_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """
        Get the system prompt for the AI model.

        Args:
            context: Optional context information

        Returns:
            System prompt for instructing the AI
        """
        default_os = context.get("default_os", "macos") if context else "macos"

        return f"""You are an expert terminal command assistant. 
    
When users request tasks:
1. Break complex tasks into individual terminal commands
2. For each command, specify:
   - The exact command with specific values where available (don't use placeholders when data is present)
   - List only required user inputs that are actually unknown
   - Specify the OS (default: {default_os})
   - Indicate if admin/root privileges are needed
   - Include a brief description of what this command does

Important rules:
- Generate ONE command per tool call
- If a task requires multiple commands, make multiple separate tool calls in sequence
- Only use placeholders for truly unknown values
- When the user mentions a specific file or directory that was clearly provided, use it directly instead of a placeholder
- For directory navigation, prefer absolute paths with '~' for home directory when appropriate
- Remember the current working directory and reference it for context
- Prefer specific, complete commands over abstract ones with placeholders
- For common directories like 'Desktop', 'Documents', 'Downloads', etc., use them directly without placeholders
- Default to {default_os} commands unless specified otherwise
- For 'cd' commands, always use the full directory path if known from context
"""

    def get_command_tool_spec(self) -> Dict[str, Any]:
        """
        Create a tool specification for function calling.

        Returns:
            Dict[str, Any]: Tool specification for command generation
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
        self,
        prompt: str,
        context: Dict[str, Any] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate commands from a natural language prompt.

        Args:
            prompt: Natural language prompt from the user
            context: Optional context information to enhance generation
            system_prompt: Optional system prompt to override default

        Returns:
            List of command dictionaries

        Raises:
            AIError: If command generation fails
        """
        # Initialize context if None to avoid NoneType errors
        if context is None:
            context = {}

        if self._using_adapter:
            try:
                # Use the adapter implementation
                messages = [{"role": "user", "content": prompt}]

                # Make sure context and history exist before trying to use them
                history = context.get("history", [])
                if history:
                    # Ensure history is a list to avoid type errors
                    if not isinstance(history, list):
                        history = [history]

                    # Ensure all history items are compatible with messages format
                    for i, item in enumerate(history):
                        if not isinstance(item, dict) or "role" not in item:
                            history[i] = {"role": "user", "content": str(item)}

                    messages = history + messages

                if not system_prompt:
                    system_prompt = self.get_system_prompt(context)

                # Convert to Message objects if model is available
                if MODELS_AVAILABLE:
                    msg_objects = []

                    # Add system message
                    msg_objects.append(
                        SystemMessage(role="system", content=system_prompt)
                    )

                    # Add history and user message
                    for msg in messages:
                        if isinstance(msg, dict):
                            if msg.get("role") == "user":
                                msg_objects.append(
                                    UserMessage(
                                        role="user", content=msg.get("content", "")
                                    )
                                )
                            elif msg.get("role") == "assistant":
                                msg_objects.append(
                                    AIMessage(
                                        role="assistant", content=msg.get("content", "")
                                    )
                                )
                        else:
                            # If message is not a dict, convert it
                            msg_objects.append(
                                UserMessage(role="user", content=str(msg))
                            )

                    tool_calls = await self.adapter.generate_commands(
                        msg_objects, system_prompt=system_prompt
                    )

                    # Convert ToolCall objects to dictionaries
                    commands = []
                    for tc in tool_calls:
                        cmd = tc.to_command()
                        if cmd:
                            commands.append(cmd.model_dump())

                    return commands
                else:
                    # Using dictionaries
                    tool_calls = await self.adapter.generate_commands(
                        messages, system_prompt=system_prompt
                    )

                    # Extract commands from tool calls
                    commands = []
                    for tc in tool_calls:
                        if tc.function_name == "get_command":
                            commands.append(tc.arguments)

                    return commands

            except Exception as e:
                raise AIError(f"Error generating commands: {e}")

        else:
            # Direct implementation using OpenAI client
            try:
                # Prepare messages
                messages = [
                    {
                        "role": "system",
                        "content": system_prompt or self.get_system_prompt(context),
                    },
                    {"role": "user", "content": prompt},
                ]

                # Make sure history exists before trying to use it
                history = context.get("history", [])
                if history:
                    # Ensure history is a list to avoid type errors
                    if not isinstance(history, list):
                        history = [history]

                    # Ensure all history items are compatible with messages format
                    for i, item in enumerate(history):
                        if not isinstance(item, dict) or "role" not in item:
                            history[i] = {"role": "user", "content": str(item)}

                    # Insert history between system message and user query
                    messages = [messages[0]] + history + [messages[-1]]

                logger.debug(f"Generating commands with {len(messages)} messages")

                # Get command tool spec
                tools = [self.get_command_tool_spec()]

                # Make API call
                response = await self.async_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=tools,
                    temperature=self.temperature,
                    tool_choice="auto",
                )

                # Check for valid response
                if not response.choices or not response.choices[0].message.tool_calls:
                    logger.warning("AI returned no tool calls")
                    return []

                # Extract commands from tool calls
                commands = []
                for tc in response.choices[0].message.tool_calls:
                    try:
                        # Parse arguments
                        args = json.loads(tc.function.arguments)
                        commands.append(args)
                    except Exception as e:
                        logger.error(f"Error parsing command: {e}")

                return commands

            except Exception as e:
                raise AIError(f"Error generating commands: {e}")

    async def invoke_tool(
        self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Invoke a specific tool with the AI provider.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments
            context: Optional context information

        Returns:
            Tool result dictionary

        Raises:
            AIError: If tool invocation fails
        """
        if self._using_adapter:
            try:
                # Create tool specification
                tool_spec = {
                    "type": "function",
                    "function": {"name": tool_name, "parameters": arguments},
                }

                # Create messages
                messages = []

                if context and "prompt" in context:
                    messages.append({"role": "user", "content": context["prompt"]})
                else:
                    messages.append(
                        {"role": "user", "content": f"Invoke {tool_name} tool"}
                    )

                # Convert to Message objects if model is available
                if MODELS_AVAILABLE:
                    msg_objects = []

                    # Add system message
                    system_prompt = context.get("system_prompt") if context else None
                    if system_prompt:
                        msg_objects.append(
                            SystemMessage(role="system", content=system_prompt)
                        )

                    # Add messages
                    for msg in messages:
                        if msg["role"] == "user":
                            msg_objects.append(
                                UserMessage(role="user", content=msg["content"])
                            )
                        elif msg["role"] == "assistant":
                            msg_objects.append(
                                AIMessage(role="assistant", content=msg["content"])
                            )

                    tool_calls = await self.adapter.invoke_tool(
                        msg_objects, tool_spec, system_prompt=system_prompt
                    )

                    if not tool_calls:
                        return {}

                    # Return the first tool call result
                    return tool_calls[0].arguments
                else:
                    # Using dictionaries
                    tool_calls = await self.adapter.invoke_tool(messages, tool_spec)

                    if not tool_calls:
                        return {}

                    # Return the first tool call result
                    return tool_calls[0].arguments

            except Exception as e:
                raise AIError(f"Error invoking tool: {e}")

        else:
            # Direct implementation using OpenAI client
            try:
                # Create tool specification
                tool_spec = {
                    "type": "function",
                    "function": {"name": tool_name, "parameters": arguments},
                }

                # Create messages
                messages = []

                # Add system message if available
                system_prompt = context.get("system_prompt") if context else None
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                # Add prompt message
                if context and "prompt" in context:
                    messages.append({"role": "user", "content": context["prompt"]})
                else:
                    messages.append(
                        {"role": "user", "content": f"Invoke {tool_name} tool"}
                    )

                logger.debug(f"Invoking tool with {len(messages)} messages")

                # Make API call
                response = await self.async_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=[tool_spec],
                    temperature=self.temperature,
                    tool_choice={"type": "function", "function": {"name": tool_name}},
                )

                # Check for valid response
                if not response.choices or not response.choices[0].message.tool_calls:
                    logger.warning("AI returned no tool calls")
                    return {}

                # Return the first tool call result
                tc = response.choices[0].message.tool_calls[0]
                return json.loads(tc.function.arguments)

            except Exception as e:
                raise AIError(f"Error invoking tool: {e}")
