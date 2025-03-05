"""
Custom exception classes for SmartTerminal.

This module defines a hierarchy of custom exception classes used throughout
the application to handle various error scenarios in a consistent way.
"""

from typing import Optional, Dict, Any


class SmartTerminalError(Exception):
    """
    Base exception class for all SmartTerminal errors.

    This is the parent class of all custom exceptions raised by the application,
    providing a common interface for error handling and consistent error reporting.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize SmartTerminalError.

        Args:
            message: Error message
            details: Optional dictionary with additional error details
            cause: Optional original exception that caused this error
        """
        self.message = message
        self.details = details or {}
        self.cause = cause

        # Construct error message with cause if available
        if cause:
            full_message = (
                f"{message} (Caused by: {type(cause).__name__}: {str(cause)})"
            )
        else:
            full_message = message

        super().__init__(full_message)


class ConfigError(SmartTerminalError):
    """
    Exception raised for configuration-related errors.

    This exception is raised when there are issues with loading, saving,
    or accessing configuration settings.
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize ConfigError.

        Args:
            message: Error message
            config_key: Optional key in the configuration that caused the error
            config_file: Optional path to the configuration file
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if config_key:
            details["config_key"] = config_key

        if config_file:
            details["config_file"] = config_file

        super().__init__(message, details=details, **kwargs)


class AIError(SmartTerminalError):
    """
    Exception raised for AI service-related errors.

    This exception is raised when there are issues communicating with
    AI services or processing AI-generated content.
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize AIError.

        Args:
            message: Error message
            provider: Optional name of the AI provider
            model: Optional model name
            status_code: Optional HTTP status code
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if provider:
            details["provider"] = provider

        if model:
            details["model"] = model

        if status_code:
            details["status_code"] = status_code

        super().__init__(message, details=details, **kwargs)


class CommandError(SmartTerminalError):
    """
    Exception raised for command execution errors.

    This exception is raised when there are issues generating or
    executing terminal commands.
    """

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize CommandError.

        Args:
            message: Error message
            command: Optional command that caused the error
            exit_code: Optional command exit code
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if command:
            details["command"] = command

        if exit_code is not None:
            details["exit_code"] = exit_code

        super().__init__(message, details=details, **kwargs)


class ShellError(SmartTerminalError):
    """
    Exception raised for shell integration errors.

    This exception is raised when there are issues with shell
    integration or shell-related operations.
    """

    def __init__(self, message: str, shell_type: Optional[str] = None, **kwargs):
        """
        Initialize ShellError.

        Args:
            message: Error message
            shell_type: Optional shell type
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if shell_type:
            details["shell_type"] = shell_type

        super().__init__(message, details=details, **kwargs)


class AdapterError(SmartTerminalError):
    """
    Exception raised for adapter-related errors.

    This exception is raised when there are issues with adapter
    initialization or operation.
    """

    def __init__(self, message: str, adapter_type: Optional[str] = None, **kwargs):
        """
        Initialize AdapterError.

        Args:
            message: Error message
            adapter_type: Optional adapter type
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if adapter_type:
            details["adapter_type"] = adapter_type

        super().__init__(message, details=details, **kwargs)


class PermissionError(SmartTerminalError):
    """
    Exception raised for permission-related errors.

    This exception is raised when the application lacks the
    necessary permissions to perform an operation.
    """

    def __init__(self, message: str, resource: Optional[str] = None, **kwargs):
        """
        Initialize PermissionError.

        Args:
            message: Error message
            resource: Optional resource for which permission was denied
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if resource:
            details["resource"] = resource

        super().__init__(message, details=details, **kwargs)


class TimeoutError(SmartTerminalError):
    """
    Exception raised when an operation times out.

    This exception is raised when an operation takes longer
    than expected or allowed.
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs,
    ):
        """
        Initialize TimeoutError.

        Args:
            message: Error message
            operation: Optional operation that timed out
            timeout_seconds: Optional timeout duration in seconds
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if operation:
            details["operation"] = operation

        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds

        super().__init__(message, details=details, **kwargs)


class ValidationError(SmartTerminalError):
    """
    Exception raised for validation errors.

    This exception is raised when input validation fails.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs,
    ):
        """
        Initialize ValidationError.

        Args:
            message: Error message
            field: Optional field that failed validation
            value: Optional invalid value
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if field:
            details["field"] = field

        if value is not None:
            details["value"] = str(value)

        super().__init__(message, details=details, **kwargs)


class NotFoundError(SmartTerminalError):
    """
    Exception raised when a resource is not found.

    This exception is raised when the application tries to
    access a resource that doesn't exist.
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize NotFoundError.

        Args:
            message: Error message
            resource_type: Optional type of resource not found
            resource_id: Optional identifier of the resource
            **kwargs: Additional keyword arguments for SmartTerminalError
        """
        details = kwargs.pop("details", {})

        if resource_type:
            details["resource_type"] = resource_type

        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(message, details=details, **kwargs)
