from smart_terminal.exceptions.errors import (
    SmartTerminalError,
    ConfigError,
    AIError,
    CommandError,
    ShellError,
    AdapterError,
    PermissionError,
    TimeoutError,
    ValidationError,
    NotFoundError,
)


def test_smart_terminal_error():
    error = SmartTerminalError(
        "An error occurred", details={"key": "value"}, cause=ValueError("Invalid value")
    )
    assert str(error) == "An error occurred (Caused by: ValueError: Invalid value)"
    assert error.details == {"key": "value"}
    assert isinstance(error.cause, ValueError)


def test_config_error():
    error = ConfigError("Config error", config_key="api_key", config_file="config.yaml")
    assert str(error) == "Config error"
    assert error.details == {"config_key": "api_key", "config_file": "config.yaml"}


def test_ai_error():
    error = AIError("AI error", provider="OpenAI", model="GPT-3", status_code=500)
    assert str(error) == "AI error"
    assert error.details == {"provider": "OpenAI", "model": "GPT-3", "status_code": 500}


def test_command_error():
    error = CommandError("Command error", command="ls -la", exit_code=1)
    assert str(error) == "Command error"
    assert error.details == {"command": "ls -la", "exit_code": 1}


def test_shell_error():
    error = ShellError("Shell error", shell_type="bash")
    assert str(error) == "Shell error"
    assert error.details == {"shell_type": "bash"}


def test_adapter_error():
    error = AdapterError("Adapter error", adapter_type="USB")
    assert str(error) == "Adapter error"
    assert error.details == {"adapter_type": "USB"}


def test_permission_error():
    error = PermissionError("Permission error", resource="file.txt")
    assert str(error) == "Permission error"
    assert error.details == {"resource": "file.txt"}


def test_timeout_error():
    error = TimeoutError(
        "Timeout error", operation="data processing", timeout_seconds=30.0
    )
    assert str(error) == "Timeout error"
    assert error.details == {"operation": "data processing", "timeout_seconds": 30.0}


def test_validation_error():
    error = ValidationError("Validation error", field="username", value="invalid_user")
    assert str(error) == "Validation error"
    assert error.details == {"field": "username", "value": "invalid_user"}


def test_not_found_error():
    error = NotFoundError("Not found error", resource_type="file", resource_id="1234")
    assert str(error) == "Not found error"
    assert error.details == {"resource_type": "file", "resource_id": "1234"}
