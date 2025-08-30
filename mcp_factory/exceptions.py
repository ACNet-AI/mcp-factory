"""MCP-Factory Exception Handling Module"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class MCPFactoryError(Exception):
    """MCP Factory unified base exception class."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        self.operation = operation
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        """String representation"""
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "operation": self.operation,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "type": self.__class__.__name__,
        }


class ConfigurationError(MCPFactoryError):
    """Configuration related exception."""

    def __init__(self, message: str, config_path: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        if config_path:
            self.details["config_path"] = config_path


class ValidationError(MCPFactoryError):
    """Validation related exception."""

    def __init__(self, message: str, validation_errors: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        if validation_errors:
            self.details["validation_errors"] = validation_errors


class ServerError(MCPFactoryError):
    """Server related exception."""

    def __init__(self, message: str, server_id: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, error_code="SERVER_ERROR", **kwargs)
        if server_id:
            self.details["server_id"] = server_id


class ProjectError(MCPFactoryError):
    """Project related exception."""

    def __init__(self, message: str, project_path: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, error_code="PROJECT_ERROR", **kwargs)
        if project_path:
            self.details["project_path"] = project_path


class MountingError(MCPFactoryError):
    """Server mounting related exception."""

    def __init__(self, message: str, mount_point: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, error_code="MOUNTING_ERROR", **kwargs)
        if mount_point:
            self.details["mount_point"] = mount_point


class BuildError(MCPFactoryError):
    """Project build related exception."""

    def __init__(self, message: str, build_target: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, error_code="BUILD_ERROR", **kwargs)
        if build_target:
            self.details["build_target"] = build_target


class ErrorMetrics:
    """Error metrics collection"""

    def __init__(self) -> None:
        self._error_counts: dict[str, int] = {}
        self._error_history: list[dict[str, Any]] = []

    def record_error(self, module: str, operation: str, error_type: str) -> None:
        """Record error metrics"""
        key = f"{module}.{operation}.{error_type}"
        self._error_counts[key] = self._error_counts.get(key, 0) + 1

        self._error_history.append(
            {
                "module": module,
                "operation": operation,
                "error_type": error_type,
                "timestamp": datetime.now().isoformat(),
                "count": self._error_counts[key],
            }
        )

        # Keep only last 1000 entries
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-1000:]

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self._error_counts.values()),
            "error_counts": self._error_counts.copy(),
            "recent_errors": self._error_history[-10:] if self._error_history else [],
        }

    def reset_metrics(self) -> None:
        """Reset all metrics"""
        self._error_counts.clear()
        self._error_history.clear()


class ErrorHandler:
    """Unified error handler"""

    def __init__(
        self,
        module_name: str = "unknown",
        logger_instance: logging.Logger | None = None,
        enable_metrics: bool = True,
        log_traceback: bool = True,
    ) -> None:
        """Initialize error handler

        Args:
            module_name: Module name for context
            logger_instance: Logger instance
            enable_metrics: Enable error metrics collection
            log_traceback: Whether to log stack trace
        """
        self.module_name = module_name
        self.logger = logger_instance or logging.getLogger(module_name)
        self.log_traceback = log_traceback
        self._error_count = 0

        # Enhanced features
        self.metrics = ErrorMetrics() if enable_metrics else None

    def handle_error(
        self, operation: str, error: Exception, context: dict[str, Any] | None = None, reraise: bool = True
    ) -> None:
        """Handle error

        Args:
            operation: Operation description
            error: Exception object
            context: Context information
            reraise: Whether to re-raise exception
        """
        self._error_count += 1
        context = context or {}

        # Record metrics
        if self.metrics:
            self.metrics.record_error(self.module_name, operation, type(error).__name__)

        # Enhanced structured logging
        self._log_structured_error(operation, error, context)

        if reraise:
            self._reraise_as_factory_error(operation, error, context)

    def _log_structured_error(self, operation: str, error: Exception, context: dict[str, Any]) -> None:
        """Log error with structured information"""
        error_data = {
            "module": self.module_name,
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "error_count": self._error_count,
        }

        if isinstance(error, MCPFactoryError):
            error_data.update(error.to_dict())

        error_msg = f"Error in {self.module_name}.{operation}: {error}"

        if self.log_traceback:
            self.logger.error("%s\nContext: %s\n%s", error_msg, context, traceback.format_exc())
        else:
            self.logger.error("%s\nContext: %s", error_msg, context)

        # Also log structured data for monitoring systems
        self.logger.debug("Structured error data: %s", error_data)

    def _reraise_as_factory_error(self, operation: str, error: Exception, context: dict[str, Any]) -> None:
        """Re-raise error as MCPFactoryError if needed"""
        if isinstance(error, MCPFactoryError):
            # Update operation if not set
            if not error.operation:
                error.operation = operation
            raise error

        # Choose appropriate exception type based on operation and context
        error_message = f"{operation} failed: {error!s}"

        if "server" in operation.lower() or "server_id" in context:
            raise ServerError(
                error_message, server_id=context.get("server_id"), operation=operation, details=context
            ) from error
        if "config" in operation.lower() or "config_path" in context:
            raise ConfigurationError(
                error_message, config_path=context.get("config_path"), operation=operation, details=context
            ) from error
        if "project" in operation.lower() or "project_path" in context:
            raise ProjectError(
                error_message, project_path=context.get("project_path"), operation=operation, details=context
            ) from error
        if "mount" in operation.lower() or "mount_point" in context:
            raise MountingError(
                error_message, mount_point=context.get("mount_point"), operation=operation, details=context
            ) from error
        if "build" in operation.lower() or "build_target" in context:
            raise BuildError(
                error_message, build_target=context.get("build_target"), operation=operation, details=context
            ) from error
        # Default to generic MCPFactoryError
        raise MCPFactoryError(message=error_message, operation=operation, details=context) from error

    def get_error_count(self) -> int:
        """Get error count"""
        return self._error_count

    def reset_error_count(self) -> None:
        """Reset error count"""
        self._error_count = 0

    def get_metrics(self) -> dict[str, Any] | None:
        """Get error metrics"""
        return self.metrics.get_error_stats() if self.metrics else None
