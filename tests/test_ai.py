"""
Tests for the ai module.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from smart_terminal.ai import AIClient, AIError, Message, Tools


class TestAIClient:
    """Tests for the AIClient class."""

    @pytest.fixture
    def mock_openai(self):
        """Create a mock OpenAI client."""
        with patch("smart_terminal.ai.OpenAI") as mock_sync:
            with patch("smart_terminal.ai.AsyncOpenAI") as mock_async:
                yield mock_sync, mock_async

    def test_init(self, mock_openai):
        """Test client initialization."""
        mock_sync, mock_async = mock_openai

        client = AIClient(
            api_key="test_key", base_url="test_url", model_name="test_model"
        )

        assert client.api_key == "test_key"
        assert client.base_url == "test_url"
        assert client.model_name == "test_model"

        # Check that the clients were initialized correctly
        mock_sync.assert_called_once_with(api_key="test_key", base_url="test_url")
        mock_async.assert_called_once_with(api_key="test_key", base_url="test_url")

    def test_init_error(self, mock_openai):
        """Test error handling during initialization."""
        mock_sync, _ = mock_openai
        mock_sync.side_effect = Exception("API init error")

        with pytest.raises(AIError) as excinfo:
            AIClient(api_key="test_key")

        assert "Failed to initialize AI client" in str(excinfo.value)

    def test_create_tool_spec(self):
        """Test creating a tool specification."""
        tool_spec = AIClient.create_tool_spec(
            name="test_tool",
            description="Tool description",
            parameters={"type": "object", "properties": {}},
        )

        assert tool_spec["type"] == "function"
        assert tool_spec["function"]["name"] == "test_tool"
        assert tool_spec["function"]["description"] == "Tool description"
        assert tool_spec["function"]["parameters"] == {
            "type": "object",
            "properties": {},
        }
        assert tool_spec["function"]["strict"] is True

    @pytest.mark.asyncio
    async def test_invoke_tool_async_success(self, mock_openai):
        """Test successful async tool invocation."""
        _, mock_async = mock_openai

        # Create mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = ["tool_call_1", "tool_call_2"]

        # Setup the mock client
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_async.return_value = mock_client

        client = AIClient(api_key="test_key")

        # Test invoking a tool
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        messages = [{"role": "user", "content": "test message"}]

        result = await client.invoke_tool_async(tools=tools, messages=messages)

        # Check the result
        assert result == ["tool_call_1", "tool_call_2"]

        # Check that the API was called correctly
        mock_client.chat.completions.create.assert_called_once_with(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools,
            temperature=0.0,
            tool_choice="auto",
        )

    @pytest.mark.asyncio
    async def test_invoke_tool_async_no_tools(self, mock_openai):
        """Test async tool invocation with no tool calls in response."""
        _, mock_async = mock_openai

        # Create mock response with no tool calls
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = None

        # Setup the mock client
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_async.return_value = mock_client

        client = AIClient(api_key="test_key")

        # Test invoking a tool
        result = await client.invoke_tool_async(
            tools=[{"type": "function"}], messages=[{"role": "user", "content": "test"}]
        )

        # Check the result is an empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_invoke_tool_async_error(self, mock_openai):
        """Test error handling in async tool invocation."""
        _, mock_async = mock_openai

        # Setup the mock client to raise an exception
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_async.return_value = mock_client

        client = AIClient(api_key="test_key")

        # Test invoking a tool with an error
        with pytest.raises(AIError) as excinfo:
            await client.invoke_tool_async(
                tools=[{"type": "function"}],
                messages=[{"role": "user", "content": "test"}],
            )

        assert "Error communicating with AI service" in str(excinfo.value)

    def test_invoke_tool_sync_success(self, mock_openai):
        """Test successful sync tool invocation."""
        mock_sync, _ = mock_openai

        # Create mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = ["tool_call_1"]

        # Setup the mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_sync.return_value = mock_client

        client = AIClient(api_key="test_key")

        # Test invoking a tool
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        messages = [{"role": "user", "content": "test message"}]

        result = client.invoke_tool_sync(tools=tools, messages=messages)

        # Check the result
        assert result == ["tool_call_1"]

        # Check that the API was called correctly
        mock_client.chat.completions.create.assert_called_once_with(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools,
            temperature=0.0,
            tool_choice="auto",
        )

    def test_invoke_tool_sync_error(self, mock_openai):
        """Test error handling in sync tool invocation."""
        mock_sync, _ = mock_openai

        # Setup the mock client to raise an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_sync.return_value = mock_client

        client = AIClient(api_key="test_key")

        # Test invoking a tool with an error
        with pytest.raises(AIError) as excinfo:
            client.invoke_tool_sync(
                tools=[{"type": "function"}],
                messages=[{"role": "user", "content": "test"}],
            )

        assert "Error communicating with AI service" in str(excinfo.value)


class TestModels:
    """Tests for the model classes."""

    def test_message_model(self):
        """Test the Message model."""
        message = Message(role="user", content="test message")
        assert message.role == "user"
        assert message.content == "test message"

        # Test serialization
        message_dict = message.model_dump()
        assert message_dict["role"] == "user"
        assert message_dict["content"] == "test message"

    def test_tools_model(self):
        """Test the Tools model."""
        tools = Tools(tools=["tool1", "tool2"])
        assert tools.tools == ["tool1", "tool2"]

        # Test serialization
        tools_dict = tools.model_dump()
        assert tools_dict["tools"] == ["tool1", "tool2"]


class TestAIError:
    """Tests for the AIError class."""

    def test_ai_error(self):
        """Test AIError exception."""
        error = AIError("Test error message")
        assert str(error) == "Test error message"
