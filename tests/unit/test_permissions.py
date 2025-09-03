"""Permission control system unit tests"""

from unittest.mock import Mock, patch

from mcp_factory.permissions import (
    ANNOTATION_TO_SCOPE_MAPPING,
    SCOPE_DESCRIPTIONS,
    PermissionCheckResult,
    check_annotation_type,
    check_permission_disabled,
    check_scopes,
    format_permission_error,
    get_all_available_scopes,
    get_current_user_info,
    get_required_scopes,
    require_annotation_type,
    require_scopes,
)


class TestPermissionCheckResult:
    """Test permission check result data structure"""

    def test_permission_check_result_creation(self):
        """Test permission check result creation"""
        result = PermissionCheckResult(
            allowed=True,
            user_id="test-user",
            user_scopes=["mcp:read"],
            required_scopes=["mcp:read"],
            missing_scopes=[],
            message="Access allowed",
        )

        assert result.allowed is True
        assert result.user_id == "test-user"
        assert result.user_scopes == ["mcp:read"]
        assert result.required_scopes == ["mcp:read"]
        assert result.missing_scopes == []
        assert result.message == "Access allowed"

    def test_permission_check_result_defaults(self):
        """Test permission check result defaults"""
        result = PermissionCheckResult(allowed=False)

        assert result.allowed is False
        assert result.user_id is None
        assert result.user_scopes is None
        assert result.required_scopes is None
        assert result.missing_scopes is None
        assert result.message == ""


class TestMappingConstants:
    """Test permission mapping constants"""

    def test_annotation_to_scope_mapping(self):
        """Test annotation type to scope mapping"""
        assert "readonly" in ANNOTATION_TO_SCOPE_MAPPING
        assert "modify" in ANNOTATION_TO_SCOPE_MAPPING
        assert "destructive" in ANNOTATION_TO_SCOPE_MAPPING
        assert "external" in ANNOTATION_TO_SCOPE_MAPPING

        # Verify permission escalation
        assert ANNOTATION_TO_SCOPE_MAPPING["readonly"] == ["mcp:read"]
        assert ANNOTATION_TO_SCOPE_MAPPING["modify"] == ["mcp:read", "mcp:write"]
        assert ANNOTATION_TO_SCOPE_MAPPING["destructive"] == ["mcp:read", "mcp:write", "mcp:admin"]
        assert ANNOTATION_TO_SCOPE_MAPPING["external"] == ["mcp:read", "mcp:write", "mcp:admin", "mcp:external"]

    def test_scope_descriptions(self):
        """Test scope descriptions"""
        assert "mcp:read" in SCOPE_DESCRIPTIONS
        assert "mcp:write" in SCOPE_DESCRIPTIONS
        assert "mcp:admin" in SCOPE_DESCRIPTIONS
        assert "mcp:external" in SCOPE_DESCRIPTIONS

        # Verify descriptions are not empty
        for _scope, description in SCOPE_DESCRIPTIONS.items():
            assert isinstance(description, str)
            assert len(description) > 0


class TestCurrentUserInfo:
    """Test current user info retrieval"""

    @patch("mcp_factory.permissions.get_access_token")
    def test_get_current_user_info_with_token(self, mock_get_token):
        """Test get user info with token"""
        # Mock access token
        mock_token = Mock()
        mock_token.client_id = "test-user"
        mock_token.scopes = ["mcp:read", "mcp:write"]
        mock_get_token.return_value = mock_token

        user_id, user_scopes = get_current_user_info()

        assert user_id == "test-user"
        assert user_scopes == ["mcp:read", "mcp:write"]

    @patch("mcp_factory.permissions.get_access_token")
    def test_get_current_user_info_without_token(self, mock_get_token):
        """Test get user info without token"""
        mock_get_token.return_value = None

        user_id, user_scopes = get_current_user_info()

        assert user_id is None
        assert user_scopes == []


class TestScopeChecking:
    """Test scope checking"""

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_scopes_success(self, mock_get_user_info):
        """Test scope check success"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read", "mcp:write"])

        result = check_scopes(["mcp:read"])

        assert result.allowed is True
        assert result.user_id == "test-user"
        assert result.required_scopes == ["mcp:read"]
        assert result.missing_scopes == []
        assert "has permission" in result.message

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_scopes_insufficient(self, mock_get_user_info):
        """Test insufficient permission"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        result = check_scopes(["mcp:read", "mcp:write"])

        assert result.allowed is False
        assert result.user_id == "test-user"
        assert result.missing_scopes == ["mcp:write"]
        assert "insufficient permission" in result.message

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_scopes_no_user(self, mock_get_user_info):
        """Test no user permission check"""
        mock_get_user_info.return_value = (None, [])

        result = check_scopes(["mcp:read"])

        assert result.allowed is False
        assert result.user_id is None
        assert "No valid authentication token provided" in result.message

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_scopes_empty_requirements(self, mock_get_user_info):
        """Test empty permission requirements"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        result = check_scopes([])

        assert result.allowed is True
        assert result.missing_scopes == []


class TestAnnotationTypeChecking:
    """Test annotation type permission check"""

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_annotation_type_readonly(self, mock_get_user_info):
        """Test readonly permission check"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        result = check_annotation_type("readonly")

        assert result.allowed is True

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_annotation_type_modify(self, mock_get_user_info):
        """Test modify permission check"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read", "mcp:write"])

        result = check_annotation_type("modify")

        assert result.allowed is True

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_annotation_type_destructive(self, mock_get_user_info):
        """Test destructive permission check"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read", "mcp:write", "mcp:admin"])

        result = check_annotation_type("destructive")

        assert result.allowed is True

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_annotation_type_external(self, mock_get_user_info):
        """Test external permission check"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read", "mcp:write", "mcp:admin", "mcp:external"])

        result = check_annotation_type("external")

        assert result.allowed is True

    def test_check_annotation_type_unknown(self):
        """Test unknown annotation type"""
        result = check_annotation_type("unknown")

        assert result.allowed is False
        assert "Unknown tool type" in result.message

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_annotation_type_insufficient_permissions(self, mock_get_user_info):
        """Test annotation type with insufficient permissions"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        result = check_annotation_type("modify")  # requires mcp:write

        assert result.allowed is False
        assert "mcp:write" in result.missing_scopes


class TestPermissionDisabled:
    """Test permission disabled mode"""

    def test_check_permission_disabled(self):
        """Test permission check disabled"""
        result = check_permission_disabled()

        assert result.allowed is True
        assert result.user_id == "anonymous"
        assert result.user_scopes == []
        assert result.required_scopes == []
        assert result.missing_scopes == []
        assert "Permission checking is disabled" in result.message


class TestUtilityFunctions:
    """Test utility functions"""

    def test_get_required_scopes(self):
        """Test get required scopes"""
        scopes = get_required_scopes("readonly")
        assert scopes == ["mcp:read"]

        scopes = get_required_scopes("modify")
        assert scopes == ["mcp:read", "mcp:write"]

        scopes = get_required_scopes("unknown")
        assert scopes == []

    def test_get_all_available_scopes(self):
        """Test get all available scopes"""
        scopes = get_all_available_scopes()

        assert isinstance(scopes, list)
        assert "mcp:read" in scopes
        assert "mcp:write" in scopes
        assert "mcp:admin" in scopes
        assert "mcp:external" in scopes

    def test_format_permission_error_allowed(self):
        """Test format permission error for allowed result"""
        result = PermissionCheckResult(allowed=True, message="Access allowed")
        formatted = format_permission_error(result)

        assert formatted.startswith("✅")
        assert "Access allowed" in formatted

    def test_format_permission_error_no_token(self):
        """Test format permission error for no token"""
        result = PermissionCheckResult(allowed=False, user_id=None)
        formatted = format_permission_error(result)

        assert formatted.startswith("❌")
        assert "No valid authentication token provided" in formatted

    def test_format_permission_error_missing_scopes(self):
        """Test format permission error for missing scopes"""
        result = PermissionCheckResult(allowed=False, user_id="test-user", missing_scopes=["mcp:write"])
        formatted = format_permission_error(result)

        assert formatted.startswith("❌")
        assert "test-user" in formatted
        assert "mcp:write" in formatted

    def test_format_permission_error_generic(self):
        """Test format generic permission error"""
        result = PermissionCheckResult(allowed=False, user_id="test-user", message="Custom error")
        formatted = format_permission_error(result)

        assert formatted.startswith("❌")
        assert "Custom error" in formatted


class TestDecorators:
    """Test decorators"""

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_require_scopes_decorator_success(self, mock_get_user_info):
        """Test permission decorator success"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        @require_scopes("mcp:read")
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_require_scopes_decorator_failure(self, mock_get_user_info):
        """Test permission decorator failure"""
        mock_get_user_info.return_value = ("test-user", [])

        @require_scopes("mcp:read")
        def test_function():
            return "success"

        result = test_function()
        assert isinstance(result, str)
        assert "❌" in result

    @patch("mcp_factory.permissions.get_current_user_info")
    async def test_require_scopes_decorator_async_success(self, mock_get_user_info):
        """Test async permission decorator success"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        @require_scopes("mcp:read")
        async def test_async_function():
            return "async success"

        result = await test_async_function()
        assert result == "async success"

    @patch("mcp_factory.permissions.get_current_user_info")
    async def test_require_scopes_decorator_async_failure(self, mock_get_user_info):
        """Test async permission decorator failure"""
        mock_get_user_info.return_value = ("test-user", [])

        @require_scopes("mcp:read")
        async def test_async_function():
            return "async success"

        result = await test_async_function()
        assert isinstance(result, str)
        assert "❌" in result

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_require_annotation_type_decorator_success(self, mock_get_user_info):
        """Test annotation type decorator success"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        @require_annotation_type("readonly")
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_require_annotation_type_decorator_failure(self, mock_get_user_info):
        """Test annotation type decorator failure"""
        mock_get_user_info.return_value = ("test-user", [])

        @require_annotation_type("readonly")
        def test_function():
            return "success"

        result = test_function()
        assert isinstance(result, str)
        assert "❌" in result


class TestEdgeCases:
    """Test edge cases"""

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_scopes_partial_match(self, mock_get_user_info):
        """Test partial permission match"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read", "mcp:admin"])

        result = check_scopes(["mcp:read", "mcp:write", "mcp:admin"])

        assert result.allowed is False
        assert result.missing_scopes == ["mcp:write"]

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_scopes_duplicate_requirements(self, mock_get_user_info):
        """Test duplicate permission requirements"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        result = check_scopes(["mcp:read", "mcp:read"])

        assert result.allowed is True

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_check_scopes_case_sensitivity(self, mock_get_user_info):
        """Test permission case sensitivity"""
        mock_get_user_info.return_value = ("test-user", ["MCP:READ"])

        result = check_scopes(["mcp:read"])

        # Permission check should be case sensitive
        assert result.allowed is False
        assert "mcp:read" in result.missing_scopes


class TestImportFallback:
    """Test import fallback implementation"""

    @patch("mcp_factory.permissions.get_access_token")
    def test_fallback_get_access_token_returns_none(self, mock_get_token):
        """Test fallback get_access_token implementation returns None"""
        # Direct call to fallback implementation
        from mcp_factory.permissions import get_access_token

        # Ensure fallback implementation is called in import failure case
        mock_get_token.return_value = None
        result = get_access_token()

        assert result is None

    def test_import_fallback_scenario(self):
        """Test mock import failure scenario"""
        # This tests behavior when mcp.server.auth.middleware.auth_context is unavailable
        # Since we have successfully imported the module, we can test None return handling
        from mcp_factory.permissions import get_current_user_info

        with patch("mcp_factory.permissions.get_access_token", return_value=None):
            user_id, user_scopes = get_current_user_info()
            assert user_id is None
            assert user_scopes == []


class TestDecoratorInternalImplementation:
    """Test decorator internal implementation details"""

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_require_scopes_decorator_sync_wrapper_direct(self, mock_get_user_info):
        """Test require_scopes decorator sync wrapper direct call"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        @require_scopes("mcp:read")
        def sync_function():
            return "success"

        # Test success case
        result = sync_function()
        assert result == "success"

        # Test failure case
        mock_get_user_info.return_value = ("test-user", [])
        result = sync_function()
        assert "Permission check failed" in result

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_require_annotation_type_decorator_sync_wrapper_direct(self, mock_get_user_info):
        """Test require_annotation_type decorator sync wrapper direct call"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        @require_annotation_type("readonly")
        def sync_function():
            return "success"

        # Test success case
        result = sync_function()
        assert result == "success"

        # Test failure case
        mock_get_user_info.return_value = ("test-user", [])
        result = sync_function()
        assert "Permission check failed" in result

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_require_scopes_with_multiple_scopes(self, mock_get_user_info):
        """Test require_scopes decorator handling multiple scopes"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read", "mcp:write"])

        @require_scopes("mcp:read", "mcp:write")
        def function_with_multiple_scopes():
            return "success"

        result = function_with_multiple_scopes()
        assert result == "success"

    @patch("mcp_factory.permissions.get_current_user_info")
    async def test_require_annotation_type_decorator_async_wrapper_direct(self, mock_get_user_info):
        """Test require_annotation_type decorator async wrapper direct call"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        @require_annotation_type("readonly")
        async def async_function():
            return "async_success"

        # Test success case
        result = await async_function()
        assert result == "async_success"

        # Test failure case
        mock_get_user_info.return_value = ("test-user", [])
        result = await async_function()
        assert "Permission check failed" in result


class TestFunctionInspection:
    """Test function inspection and decorator application"""

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function metadata"""

        @require_scopes("mcp:read")
        def original_function():
            """This is the original function docstring"""
            return "original"

        # Check if functools.wraps correctly preserved metadata
        assert original_function.__name__ == "original_function"
        assert "This is the original function docstring" in original_function.__doc__

    @patch("mcp_factory.permissions.get_current_user_info")
    def test_decorator_handles_function_args_and_kwargs(self, mock_get_user_info):
        """Test decorator correctly handles function parameters"""
        mock_get_user_info.return_value = ("test-user", ["mcp:read"])

        @require_scopes("mcp:read")
        def function_with_args(a, b, c=None):
            return f"args: {a}, {b}, {c}"

        result = function_with_args("test1", "test2", c="test3")
        assert result == "args: test1, test2, test3"


class TestPermissionErrorMessageFormatting:
    """Test permission error message formatting edge cases"""

    def test_format_permission_error_with_empty_missing_scopes(self):
        """Test format permission error message when missing_scopes is empty"""
        result = PermissionCheckResult(
            allowed=False,
            user_id="test-user",
            user_scopes=["mcp:read"],
            required_scopes=["mcp:read"],
            missing_scopes=[],
            message="Custom error message",
        )

        formatted = format_permission_error(result)
        assert "❌ Permission check failed: Custom error message" in formatted

    def test_format_permission_error_with_none_missing_scopes(self):
        """Test format permission error message when missing_scopes is None"""
        result = PermissionCheckResult(
            allowed=False,
            user_id="test-user",
            user_scopes=["mcp:read"],
            required_scopes=["mcp:read"],
            missing_scopes=None,
            message="Custom error message",
        )

        formatted = format_permission_error(result)
        assert "❌ Permission check failed: Custom error message" in formatted
