"""
Helper functions for SmartTerminal.

This module provides general-purpose utility functions that are used
throughout the application but don't fit into more specific categories.
"""

import os
import sys
import json
import inspect
import warnings
import platform
import functools
import subprocess
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Callable,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from smart_terminal.utils.colors import Colors

# Define type variables for generic functions
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")
R = TypeVar("R")


def print_error(message: str) -> None:
    """
    Print an error message to the console.

    Args:
        message: The error message to print
    """
    print(Colors.error(f"Error: {message}"))


def print_warning(message: str) -> None:
    """
    Print a warning message to the console.

    Args:
        message: The warning message to print
    """
    print(Colors.warning(f"Warning: {message}"))


def print_success(message: str) -> None:
    """
    Print a success message to the console.

    Args:
        message: The success message to print
    """
    print(Colors.success(message))


def print_info(message: str) -> None:
    """
    Print an informational message to the console.

    Args:
        message: The informational message to print
    """
    print(Colors.info(message))


def print_banner() -> None:
    """Print a fancy banner for the application."""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════╗
║                                                  ║
║  {Colors.GREEN}SmartTerminal{Colors.CYAN}                                   ║
║  {Colors.BLUE}AI-Powered Terminal Commands{Colors.CYAN}                    ║
║                                                  ║
╚══════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def safe_execute(
    func: Callable[..., R],
    *args: Any,
    default: Optional[R] = None,
    error_message: Optional[str] = None,
    **kwargs: Any,
) -> R:
    """
    Execute a function safely, handling any exceptions.

    Args:
        func: Function to execute
        *args: Positional arguments to pass to the function
        default: Default value to return if function raises an exception
        error_message: Optional error message to print if function raises an exception
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Result of the function or default value if an exception occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_message:
            print_error(f"{error_message}: {e}")
        return cast(R, default)


def parse_json(json_str: str) -> Dict[str, Any]:
    """
    Parse a JSON string into a dictionary.

    Args:
        json_str: JSON string to parse

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If JSON parsing fails
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")


def get_os_type() -> str:
    """
    Get the current operating system type.

    Returns:
        One of: 'macos', 'linux', 'windows', or 'unknown'
    """
    system = platform.system().lower()

    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    else:
        return "unknown"


def get_username() -> str:
    """
    Get the current username.

    Returns:
        Current username or 'user' if not available
    """
    return os.environ.get("USER", os.environ.get("USERNAME", "user"))


def get_hostname() -> str:
    """
    Get the current hostname.

    Returns:
        Current hostname or 'localhost' if not available
    """
    return platform.node() or "localhost"


def is_command_available(command: str) -> bool:
    """
    Check if a command is available in the PATH.

    Args:
        command: Command to check

    Returns:
        True if the command is available, False otherwise
    """
    try:
        subprocess.run(
            ["which", command] if get_os_type() != "windows" else ["where", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string if it exceeds a maximum length.

    Args:
        text: String to truncate
        max_length: Maximum length of the string
        suffix: Suffix to add to truncated strings

    Returns:
        Truncated string with suffix if truncated, original string otherwise
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def human_readable_size(size_bytes: int) -> str:
    """
    Convert a size in bytes to a human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.2 MB")
    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]

    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {units[i]}"


def human_readable_time(seconds: float) -> str:
    """
    Convert a time in seconds to a human-readable string.

    Args:
        seconds: Time in seconds

    Returns:
        Human-readable time string (e.g., "1h 2m 3s")
    """
    if seconds < 1:
        ms = seconds * 1000
        return f"{ms:.0f}ms"

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    parts = []
    if h > 0:
        parts.append(f"{h:.0f}h")
    if m > 0:
        parts.append(f"{m:.0f}m")
    if s > 0 or not parts:
        parts.append(f"{s:.0f}s")

    return " ".join(parts)


def execute_with_timeout(
    func: Callable[..., R], timeout: float, *args: Any, **kwargs: Any
) -> Tuple[bool, Optional[R], Optional[Exception]]:
    """
    Execute a function with a timeout.

    Args:
        func: Function to execute
        timeout: Timeout in seconds
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Tuple of (success, result, exception)
    """
    import threading

    result: List[Union[R, Exception]] = []
    exception: List[Exception] = []
    success = [False]

    def target() -> None:
        try:
            result.append(func(*args, **kwargs))
            success[0] = True
        except Exception as e:
            exception.append(e)

    thread = threading.Thread(target=target)
    thread.daemon = True

    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return False, None, TimeoutError(f"Function timed out after {timeout} seconds")

    if success[0]:
        return True, cast(R, result[0]), None

    return False, None, exception[0] if exception else None


def is_admin() -> bool:
    """
    Check if the current process is running with administrator privileges.

    Returns:
        True if running as admin/root, False otherwise
    """
    if get_os_type() == "windows":
        try:
            return bool(
                subprocess.run(
                    ["net", "session"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ).returncode
                == 0
            )
        except Exception:
            return False
    else:
        return os.geteuid() == 0  # type: ignore


def get_terminal_size() -> Tuple[int, int]:
    """
    Get the current terminal size.

    Returns:
        Tuple of (width, height) in characters
    """
    try:
        columns, lines = os.get_terminal_size(0)
        return columns, lines
    except (OSError, AttributeError):
        return 80, 24  # Default fallback size


def is_interactive_shell() -> bool:
    """
    Check if we're running in an interactive shell.

    Returns:
        True if running in an interactive shell, False otherwise
    """
    return sys.stdin.isatty() and sys.stdout.isatty()


def clear_screen() -> None:
    """Clear the terminal screen."""
    os_type = get_os_type()
    if os_type == "windows":
        os.system("cls")
    else:
        os.system("clear")


@overload
def deprecated(func: F) -> F: ...


@overload
def deprecated(
    func: None = None,
    message: Optional[str] = None,
    version: Optional[str] = None,
    alternative: Optional[str] = None,
    category: Type[Warning] = DeprecationWarning,
    stacklevel: int = 2,
) -> Callable[[F], F]: ...


def deprecated(
    func: Optional[Callable] = None,
    message: Optional[str] = None,
    version: Optional[str] = None,
    alternative: Optional[str] = None,
    category: type[Warning] = DeprecationWarning,
    stacklevel: int = 2,
) -> Any:
    """
    Decorator to mark functions, methods, or classes as deprecated.

    Args:
        func: The function, method, or class being decorated
        message: Optional custom deprecation message
        version: Optional version when the decorated object will be removed
        alternative: Optional name of alternative function/method/class to use
        category: Warning category to use, defaults to DeprecationWarning
        stacklevel: Controls warning stacktrace depth

    Returns:
        Decorated function, method, or class that issues a deprecation warning when used

    Examples:
        Basic usage:
        >>> @deprecated
        ... def old_function():
        ...     pass

        With custom message:
        >>> @deprecated(message="Use another function")
        ... def old_function():
        ...     pass

        With version and alternative:
        >>> @deprecated(version="2.0.0", alternative="new_function")
        ... def old_function():
        ...     pass
    """

    def decorator(func_or_class: F) -> F:
        # Get object name and type
        is_class = inspect.isclass(func_or_class)
        obj_name = func_or_class.__qualname__
        obj_type = "class" if is_class else "function"

        # Build the deprecation message
        msg_parts = []

        if message:
            msg_parts.append(message)
        else:
            msg_parts.append(f"{obj_type.capitalize()} {obj_name} is deprecated.")

        if version:
            msg_parts.append(f"It will be removed in version {version}.")

        if alternative:
            msg_parts.append(f"Use {alternative} instead.")

        complete_message = " ".join(msg_parts)

        # Class decorator
        if is_class:
            original_init = func_or_class.__init__

            @functools.wraps(original_init)
            def wrapped_init(self, *args, **kwargs):
                warnings.warn(
                    complete_message, category=category, stacklevel=stacklevel
                )
                return original_init(self, *args, **kwargs)

            func_or_class.__init__ = wrapped_init
            return cast(F, func_or_class)

        # Function/method decorator
        @functools.wraps(func_or_class)
        def wrapper(*args, **kwargs):
            warnings.warn(complete_message, category=category, stacklevel=stacklevel)
            return func_or_class(*args, **kwargs)

        return cast(F, wrapper)

    # Handle both @deprecated and @deprecated() syntax
    if func is None:
        return decorator

    return decorator(func)
