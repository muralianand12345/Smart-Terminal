"""
Message models for SmartTerminal.

This module defines models for representing chat messages between the user
and the AI, including system messages and tool calls.
"""

from abc import ABC
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


class Message(BaseModel, ABC):
    """
    Base class for all chat messages.

    This is the abstract base class for all types of messages that can
    be exchanged between the user and the AI.
    """

    role: str = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The content of the message")

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to a dictionary suitable for API calls."""
        return self.model_dump()


class UserMessage(Message):
    """
    A message from the user to the AI.

    This represents natural language queries from the user that
    need to be processed by the AI.
    """

    role: Literal["user"] = Field(
        default="user", description="The role of the message sender"
    )

    @classmethod
    def create(cls, content: str) -> "UserMessage":
        """
        Create a new user message.

        Args:
            content: The message content

        Returns:
            A new UserMessage instance
        """
        return cls(role="user", content=content)


class SystemMessage(Message):
    """
    A system message setting the behavior of the AI.

    This represents instructions to the AI about how it should
    behave or process the user's requests.
    """

    role: Literal["system"] = Field(
        default="system", description="The role of the message sender"
    )

    @classmethod
    def create(cls, content: str) -> "SystemMessage":
        """
        Create a new system message.

        Args:
            content: The message content

        Returns:
            A new SystemMessage instance
        """
        return cls(role="system", content=content)


class ToolCallInfo(BaseModel):
    """Information about a tool call made by the AI."""

    id: str = Field(..., description="Unique identifier for this tool call")
    type: str = Field(..., description="Type of the tool call")
    function: Dict[str, Any] = Field(..., description="Function call information")


class AIMessage(Message):
    """
    A message from the AI to the user.

    This represents responses from the AI, which might include
    natural language text, tool calls, or both.
    """

    role: Literal["assistant"] = Field(
        default="assistant", description="The role of the message sender"
    )
    content: Optional[str] = Field(
        default=None, description="The content of the message"
    )
    tool_calls: Optional[List[ToolCallInfo]] = Field(
        default=None, description="Tool calls made by the AI"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to a dictionary suitable for API calls."""
        result = {"role": self.role}

        if self.content is not None:
            result["content"] = self.content

        if self.tool_calls is not None:
            result["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]

        return result

    @classmethod
    def create(
        cls,
        content: Optional[str] = None,
        tool_calls: Optional[List[ToolCallInfo]] = None,
    ) -> "AIMessage":
        """
        Create a new AI message.

        Args:
            content: The message content (optional)
            tool_calls: List of tool calls (optional)

        Returns:
            A new AIMessage instance
        """
        return cls(role="assistant", content=content, tool_calls=tool_calls)


class ChatHistory(BaseModel):
    """
    Represents a conversation history between the user and the AI.

    This model maintains a list of messages and provides methods
    for adding new messages and serializing the history.
    """

    messages: List[Message] = Field(default_factory=list)

    def add_message(self, message: Message) -> None:
        """
        Add a message to the history.

        Args:
            message: The message to add
        """
        self.messages.append(message)

    def to_list(self) -> List[Dict[str, Any]]:
        """
        Convert the history to a list of message dictionaries.

        Returns:
            List of message dictionaries suitable for API calls
        """
        return [message.to_dict() for message in self.messages]

    def clear(self) -> None:
        """Clear all messages from the history."""
        self.messages = []
