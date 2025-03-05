import pytest

from smart_terminal.utils.helpers import (
    print_error,
    print_warning,
    print_success,
    print_info,
    safe_execute,
    parse_json,
    get_os_type,
    get_username,
    get_hostname,
    is_command_available,
    truncate_string,
    human_readable_size,
    human_readable_time,
    execute_with_timeout,
    is_admin,
    get_terminal_size,
    is_interactive_shell,
    clear_screen,
)


def test_print_functions(capsys):
    print_error("Error message")
    captured = capsys.readouterr()
    assert "Error: Error message" in captured.out

    print_warning("Warning message")
    captured = capsys.readouterr()
    assert "Warning: Warning message" in captured.out

    print_success("Success message")
    captured = capsys.readouterr()
    assert "Success message" in captured.out

    print_info("Info message")
    captured = capsys.readouterr()
    assert "Info message" in captured.out


def test_safe_execute():
    def func(x):
        return x * 2

    assert safe_execute(func, 2) == 4
    assert safe_execute(func, "a") == "aa"
    assert safe_execute(lambda: 1 / 0, default="error") == "error"


def test_parse_json():
    assert parse_json('{"key": "value"}') == {"key": "value"}
    with pytest.raises(ValueError):
        parse_json("invalid json")


def test_get_os_type():
    assert get_os_type() in ["macos", "linux", "windows", "unknown"]


def test_get_username():
    assert isinstance(get_username(), str)


def test_get_hostname():
    assert isinstance(get_hostname(), str)


def test_is_command_available():
    assert is_command_available("python")


def test_truncate_string():
    assert truncate_string("Hello, world!", 5) == "He..."


def test_human_readable_size():
    assert human_readable_size(1024) == "1.0 KB"


def test_human_readable_time():
    assert human_readable_time(3661) == "1h 1m 1s"


def test_execute_with_timeout():
    def func(x):
        return x * 2

    success, result, exception = execute_with_timeout(func, 1, 2)
    assert success
    assert result == 4
    assert exception is None


def test_is_admin():
    assert isinstance(is_admin(), bool)


def test_get_terminal_size():
    assert isinstance(get_terminal_size(), tuple)


def test_is_interactive_shell():
    assert isinstance(is_interactive_shell(), bool)


def test_clear_screen():
    clear_screen()
