"""Test cases for MCP Factory exception handling"""

import logging
from datetime import datetime
from unittest.mock import Mock

import pytest

from mcp_factory.exceptions import (
    BuildError,
    ConfigurationError,
    ErrorHandler,
    ErrorMetrics,
    MCPFactoryError,
    MountingError,
    ProjectError,
    ServerError,
    ValidationError,
)


class TestMCPFactoryError:
    """Test MCPFactoryError base class"""

    def test_basic_exception_creation(self):
        """Test basic exception creation"""
        error = MCPFactoryError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}
        assert error.error_code is None
        assert error.operation is None
        assert isinstance(error.timestamp, datetime)

    def test_exception_with_details(self):
        """Test exception with details"""
        details = {"key": "value", "count": 42}
        error = MCPFactoryError("Test error", details=details)

        assert error.details == details
        assert error.details["key"] == "value"
        assert error.details["count"] == 42

    def test_exception_with_error_code(self):
        """Test exception with error code"""
        error = MCPFactoryError("Test error", error_code="TEST_ERROR")

        assert error.error_code == "TEST_ERROR"

    def test_exception_with_operation(self):
        """Test exception with operation"""
        error = MCPFactoryError("Test error", operation="test_operation")

        assert error.operation == "test_operation"

    def test_to_dict_method(self):
        """Test to_dict serialization"""
        error = MCPFactoryError(
            "Test error",
            details={"key": "value"},
            error_code="TEST_ERROR",
            operation="test_op"
        )

        result = error.to_dict()

        assert result["message"] == "Test error"
        assert result["error_code"] == "TEST_ERROR"
        assert result["operation"] == "test_op"
        assert result["details"] == {"key": "value"}
        assert result["type"] == "MCPFactoryError"
        assert "timestamp" in result


class TestSpecificExceptions:
    """Test specific exception types"""

    def test_configuration_error(self):
        """Test ConfigurationError"""
        error = ConfigurationError("Config error", config_path="/path/to/config.yaml")

        assert isinstance(error, MCPFactoryError)
        assert str(error) == "Config error"
        assert error.error_code == "CONFIG_ERROR"
        assert error.details["config_path"] == "/path/to/config.yaml"

    def test_validation_error(self):
        """Test ValidationError"""
        validation_errors = ["Field is required", "Invalid format"]
        error = ValidationError("Validation failed", validation_errors=validation_errors)

        assert isinstance(error, MCPFactoryError)
        assert str(error) == "Validation failed"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.details["validation_errors"] == validation_errors

    def test_server_error(self):
        """Test ServerError"""
        error = ServerError("Server failed", server_id="srv-123")

        assert isinstance(error, MCPFactoryError)
        assert str(error) == "Server failed"
        assert error.error_code == "SERVER_ERROR"
        assert error.details["server_id"] == "srv-123"

    def test_project_error(self):
        """Test ProjectError"""
        error = ProjectError("Project error", project_path="/path/to/project")

        assert isinstance(error, MCPFactoryError)
        assert str(error) == "Project error"
        assert error.error_code == "PROJECT_ERROR"
        assert error.details["project_path"] == "/path/to/project"

    def test_mounting_error(self):
        """Test MountingError"""
        error = MountingError("Mount failed", mount_point="/mnt/point")

        assert isinstance(error, MCPFactoryError)
        assert str(error) == "Mount failed"
        assert error.error_code == "MOUNTING_ERROR"
        assert error.details["mount_point"] == "/mnt/point"

    def test_build_error(self):
        """Test BuildError"""
        error = BuildError("Build failed", build_target="production")

        assert isinstance(error, MCPFactoryError)
        assert str(error) == "Build failed"
        assert error.error_code == "BUILD_ERROR"
        assert error.details["build_target"] == "production"


class TestErrorMetrics:
    """Test error metrics functionality"""

    def test_metrics_initialization(self):
        """Test metrics initialization"""
        metrics = ErrorMetrics()

        assert metrics._error_counts == {}
        assert metrics._error_history == []

    def test_record_error(self):
        """Test error recording"""
        metrics = ErrorMetrics()

        metrics.record_error("test_module", "test_operation", "ValueError")

        assert metrics._error_counts["test_module.test_operation.ValueError"] == 1
        assert len(metrics._error_history) == 1

        history_entry = metrics._error_history[0]
        assert history_entry["module"] == "test_module"
        assert history_entry["operation"] == "test_operation"
        assert history_entry["error_type"] == "ValueError"
        assert history_entry["count"] == 1

    def test_multiple_error_recording(self):
        """Test multiple error recording"""
        metrics = ErrorMetrics()

        metrics.record_error("module1", "op1", "ValueError")
        metrics.record_error("module1", "op1", "ValueError")
        metrics.record_error("module2", "op2", "TypeError")

        assert metrics._error_counts["module1.op1.ValueError"] == 2
        assert metrics._error_counts["module2.op2.TypeError"] == 1
        assert len(metrics._error_history) == 3

    def test_get_error_stats(self):
        """Test error statistics"""
        metrics = ErrorMetrics()

        metrics.record_error("module1", "op1", "ValueError")
        metrics.record_error("module2", "op2", "TypeError")

        stats = metrics.get_error_stats()

        assert stats["total_errors"] == 2
        assert "module1.op1.ValueError" in stats["error_counts"]
        assert "module2.op2.TypeError" in stats["error_counts"]
        assert len(stats["recent_errors"]) == 2

    def test_reset_metrics(self):
        """Test metrics reset"""
        metrics = ErrorMetrics()

        metrics.record_error("module1", "op1", "ValueError")
        metrics.reset_metrics()

        assert metrics._error_counts == {}
        assert metrics._error_history == []


class TestErrorHandler:
    """Test error handler functionality"""

    def test_error_handler_initialization(self):
        """Test error handler initialization"""
        handler = ErrorHandler("test_module")

        assert handler.module_name == "test_module"
        assert handler.logger is not None
        assert handler.log_traceback is True
        assert handler._error_count == 0
        assert handler.metrics is not None

    def test_error_handler_with_custom_logger(self):
        """Test error handler with custom logger"""
        custom_logger = Mock(spec=logging.Logger)
        handler = ErrorHandler("test_module", logger_instance=custom_logger)

        assert handler.logger is custom_logger

    def test_error_handler_without_metrics(self):
        """Test error handler without metrics"""
        handler = ErrorHandler("test_module", enable_metrics=False)

        assert handler.metrics is None

    def test_handle_error_basic(self):
        """Test basic error handling"""
        mock_logger = Mock(spec=logging.Logger)
        handler = ErrorHandler("test_module", logger_instance=mock_logger)

        test_error = ValueError("Test error")

        with pytest.raises(MCPFactoryError) as exc_info:
            handler.handle_error("test_operation", test_error)

        # Check that error was wrapped
        wrapped_error = exc_info.value
        assert "test_operation failed: Test error" in str(wrapped_error)
        assert wrapped_error.operation == "test_operation"

        # Check that logging occurred
        assert mock_logger.error.called

    def test_handle_error_with_context(self):
        """Test error handling with context"""
        mock_logger = Mock(spec=logging.Logger)
        handler = ErrorHandler("test_module", logger_instance=mock_logger)

        test_error = ValueError("Test error")
        context = {"user_id": "123", "action": "test"}

        with pytest.raises(MCPFactoryError) as exc_info:
            handler.handle_error("test_operation", test_error, context=context)

        wrapped_error = exc_info.value
        assert wrapped_error.details == context

    def test_handle_mcp_factory_error_passthrough(self):
        """Test MCPFactoryError passthrough"""
        mock_logger = Mock(spec=logging.Logger)
        handler = ErrorHandler("test_module", logger_instance=mock_logger)

        test_error = ConfigurationError("Config error")

        with pytest.raises(ConfigurationError) as exc_info:
            handler.handle_error("test_operation", test_error)

        # Should be the same error, but with operation set
        assert exc_info.value is test_error
        assert exc_info.value.operation == "test_operation"

    def test_handle_error_no_reraise(self):
        """Test error handling without re-raising"""
        mock_logger = Mock(spec=logging.Logger)
        handler = ErrorHandler("test_module", logger_instance=mock_logger)

        test_error = ValueError("Test error")

        # Should not raise
        handler.handle_error("test_operation", test_error, reraise=False)

        # Check that error count increased
        assert handler.get_error_count() == 1

    def test_error_count_tracking(self):
        """Test error count tracking"""
        mock_logger = Mock(spec=logging.Logger)
        handler = ErrorHandler("test_module", logger_instance=mock_logger)

        assert handler.get_error_count() == 0

        # Handle multiple errors without re-raising
        handler.handle_error("op1", ValueError("error1"), reraise=False)
        handler.handle_error("op2", TypeError("error2"), reraise=False)

        assert handler.get_error_count() == 2

        # Reset count
        handler.reset_error_count()
        assert handler.get_error_count() == 0

    def test_get_metrics(self):
        """Test metrics retrieval"""
        handler = ErrorHandler("test_module")

        # Handle some errors
        handler.handle_error("op1", ValueError("error1"), reraise=False)
        handler.handle_error("op2", TypeError("error2"), reraise=False)

        metrics = handler.get_metrics()

        assert metrics is not None
        assert metrics["total_errors"] == 2
        assert "test_module.op1.ValueError" in metrics["error_counts"]
        assert "test_module.op2.TypeError" in metrics["error_counts"]

    def test_get_metrics_disabled(self):
        """Test metrics retrieval when disabled"""
        handler = ErrorHandler("test_module", enable_metrics=False)

        assert handler.get_metrics() is None


class TestIntegration:
    """Integration tests"""

    def test_full_error_flow(self):
        """Test complete error handling flow"""
        handler = ErrorHandler("integration_test")

        # Create a configuration error
        config_error = ConfigurationError(
            "Invalid configuration",
            config_path="/path/to/config.yaml"
        )

        # Handle the error
        with pytest.raises(ConfigurationError) as exc_info:
            handler.handle_error("load_config", config_error, context={"source": "file"})

        # Verify error properties
        error = exc_info.value
        assert error.operation == "load_config"
        assert error.error_code == "CONFIG_ERROR"
        assert error.details["config_path"] == "/path/to/config.yaml"

        # Verify metrics
        metrics = handler.get_metrics()
        assert metrics["total_errors"] == 1
        assert "integration_test.load_config.ConfigurationError" in metrics["error_counts"]
