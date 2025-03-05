import os
import pytest
from unittest.mock import patch, AsyncMock

from smart_terminal.core.terminal import SmartTerminal
from smart_terminal.exceptions import SmartTerminalError, AIError


@pytest.fixture
def mock_config():
    return {
        "api_key": "test_api_key",
        "base_url": "https://api.groq.com/openai/v1",
        "model_name": "llama-3.3-70b-versatile",
        "temperature": 0.0,
        "history_limit": 5,
        "shell_integration_enabled": False,
    }


@pytest.fixture
def smart_terminal(mock_config):
    with patch(
        "smart_terminal.config.ConfigManager.load_config", return_value=mock_config
    ):
        return SmartTerminal()


def test_initialization(smart_terminal, mock_config):
    assert smart_terminal.config == mock_config
    assert smart_terminal.current_directory == os.getcwd()
    assert smart_terminal.dry_run is False
    assert smart_terminal.json_output is False
    assert smart_terminal.shell_integration is not None
    assert smart_terminal.ai_client is not None
    assert smart_terminal.command_generator is not None
    assert smart_terminal.command_executor is not None
    assert smart_terminal.context_generator is not None


@pytest.mark.asyncio
async def test_process_input_success(smart_terminal):
    user_query = "list all files"
    mock_commands = [
        {
            "command": "ls -la",
            "user_inputs": [],
            "requires_admin": False,
            "description": "List all files",
        }
    ]

    with patch.object(
        smart_terminal.command_generator,
        "generate_commands",
        new=AsyncMock(return_value=mock_commands),
    ):
        with patch.object(
            smart_terminal.command_executor, "process_commands", return_value=True
        ):
            result = await smart_terminal.process_input(user_query)
            assert result is True


@pytest.mark.asyncio
async def test_process_input_no_commands(smart_terminal):
    user_query = "list all files"

    with patch.object(
        smart_terminal.command_generator,
        "generate_commands",
        new=AsyncMock(return_value=[]),
    ):
        result = await smart_terminal.process_input(user_query)
        assert result is False


@pytest.mark.asyncio
async def test_process_input_ai_error(smart_terminal):
    user_query = "list all files"

    with patch.object(
        smart_terminal.command_generator,
        "generate_commands",
        new=AsyncMock(side_effect=AIError("AI error")),
    ):
        result = await smart_terminal.process_input(user_query)
        assert result is False


@pytest.mark.asyncio
async def test_process_input_unexpected_error(smart_terminal):
    user_query = "list all files"

    with patch.object(
        smart_terminal.command_generator,
        "generate_commands",
        new=AsyncMock(side_effect=Exception("Unexpected error")),
    ):
        result = await smart_terminal.process_input(user_query)
        assert result is False
