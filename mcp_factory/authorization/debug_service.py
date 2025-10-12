"""
Debug Service - Permission debugging and diagnostic tools

This module provides comprehensive debugging and diagnostic
functionality for the authorization system.
"""

import logging
from typing import Any

from .models import DEFAULT_ROLES

logger = logging.getLogger(__name__)


class DebugService:
    """Permission debugging and diagnostic service"""

    def __init__(self, enforcer: Any, db_path: str, role_service: Any, permission_engine: Any) -> None:
        """
        Initialize debug service

        Args:
            enforcer: Casbin enforcer instance
            db_path: Database path
            role_service: Role service instance
            permission_engine: Permission engine instance
        """
        self.enforcer = enforcer
        self.db_path = db_path
        self.role_service = role_service
        self.permission_engine = permission_engine

    def debug_permission(self, user_id: str, resource: str, action: str, scope: str = "*") -> dict:
        """
        Debug permission check process, providing detailed diagnostic information

        Args:
            user_id: User ID
            resource: Resource type
            action: Action type
            scope: Scope

        Returns:
            dict: Detailed debug information
        """
        debug_info = {
            "request": {"user_id": user_id, "resource": resource, "action": action, "scope": scope},
            "user_info": {},
            "permission_check": {},
            "diagnosis": [],
            "suggestions": [],
        }

        try:
            # 1. Get user basic information
            user_roles = self.role_service.get_user_roles(user_id)
            user_permissions = self.role_service.get_user_permissions(user_id)

            debug_info["user_info"] = {
                "roles": user_roles,
                "direct_permissions": user_permissions,
                "has_roles": len(user_roles) > 0,
                "has_permissions": len(user_permissions) > 0,
            }

            # 2. Execute permission check
            casbin_result = self.enforcer.enforce(user_id, resource, action, scope)
            temp_result = self.permission_engine._check_temporary_permission(user_id, resource, action, scope)
            final_result = casbin_result or temp_result

            debug_info["permission_check"] = {
                "casbin_result": casbin_result,
                "temporary_permission": temp_result,
                "final_result": final_result,
            }

            # 3. Analyze matching policies
            matching_policies = self._find_matching_policies(user_id, resource, action, scope)
            debug_info["matching_policies"] = matching_policies  # type: ignore[assignment]

            # 4. Diagnose common issues
            diagnosis = self._diagnose_permission_issues(user_id, resource, action, scope, debug_info)
            debug_info["diagnosis"] = diagnosis

            # 5. Provide suggestions
            suggestions = self._generate_permission_suggestions(user_id, resource, action, scope, debug_info)
            debug_info["suggestions"] = suggestions

            return debug_info

        except Exception as e:
            logger.error(f"Error in debug_permission: {e}")
            debug_info["error"] = str(e)
            return debug_info

    def _find_matching_policies(self, user_id: str, resource: str, action: str, scope: str) -> list[dict]:
        """Find matching policies"""
        matching_policies = []

        try:
            # Get all user roles
            user_roles = self.role_service.get_user_roles(user_id)
            all_subjects = [user_id] + user_roles

            # Get all policies
            all_policies = self.enforcer.get_policy()

            for policy in all_policies:
                if len(policy) >= 4:
                    policy_subject, policy_resource, policy_action, policy_scope = policy[:4]
                    policy_effect = policy[4] if len(policy) > 4 else "allow"

                    # Check if matches
                    subject_match = policy_subject in all_subjects
                    resource_match = policy_resource == resource
                    action_match = policy_action == action
                    scope_match = policy_scope == "*" or policy_scope == scope

                    if subject_match and resource_match and action_match and scope_match:
                        matching_policies.append(
                            {
                                "subject": policy_subject,
                                "resource": policy_resource,
                                "action": policy_action,
                                "scope": policy_scope,
                                "effect": policy_effect,
                                "matches": {
                                    "subject": subject_match,
                                    "resource": resource_match,
                                    "action": action_match,
                                    "scope": scope_match,
                                },
                            }
                        )

            return matching_policies

        except Exception as e:
            logger.error(f"Error finding matching policies: {e}")
            return []

    def _diagnose_permission_issues(
        self, user_id: str, resource: str, action: str, scope: str, debug_info: dict
    ) -> list[str]:
        """Diagnose permission issues"""
        diagnosis = []

        # Check if user exists
        if not debug_info["user_info"]["has_roles"] and not debug_info["user_info"]["has_permissions"]:
            diagnosis.append("❌ User has no assigned roles or permissions")

        # Check if there are matching policies
        if not debug_info.get("matching_policies"):
            diagnosis.append("❌ No matching permission policies found")

            # Further analyze the cause
            user_roles = debug_info["user_info"]["roles"]
            if not user_roles:
                diagnosis.append("💡 Reason: User has no assigned roles")
            else:
                diagnosis.append(f"💡 User roles: {', '.join(user_roles)}")
                diagnosis.append(f"💡 Please check if roles have {resource}:{action}:{scope} permission")

        # Check permission check results
        if not debug_info["permission_check"]["final_result"]:
            if debug_info["permission_check"]["casbin_result"]:
                diagnosis.append("✅ Casbin permission check passed")
            else:
                diagnosis.append("❌ Casbin permission check failed")

            if debug_info["permission_check"]["temporary_permission"]:
                diagnosis.append("✅ Temporary permission check passed")
            else:
                diagnosis.append("❌ Temporary permission check failed")

        return diagnosis

    def _generate_permission_suggestions(
        self, user_id: str, resource: str, action: str, scope: str, debug_info: dict
    ) -> list[str]:
        """Generate permission configuration suggestions"""
        suggestions = []

        if not debug_info["permission_check"]["final_result"]:
            # Suggest assigning suitable roles
            suitable_roles = self._find_suitable_roles(resource, action, scope)
            if suitable_roles:
                suggestions.append(f"💡 Suggest assigning one of the following roles: {', '.join(suitable_roles)}")
                for role in suitable_roles:
                    suggestions.append(
                        f"   Execute: auth_manager.assign_role('{user_id}', '{role}', 'admin', 'Permission debug suggestion')"
                    )

            # Suggest adding temporary permissions
            suggestions.append("💡 Or add temporary permissions:")
            suggestions.append(
                f"   Execute: auth_manager.grant_temporary_permission('{user_id}', '{resource}', '{action}', '{scope}', expires_in_hours=24)"
            )

            # Suggest checking permission configuration
            suggestions.append("💡 Check permission configuration:")
            suggestions.append("   1. Confirm user has been assigned correct roles")
            suggestions.append("   2. Confirm roles have required permissions")
            suggestions.append("   3. Check if permission policies are loaded correctly")

        return suggestions

    def _find_suitable_roles(self, resource: str, action: str, scope: str) -> list[str]:
        """Find suitable roles"""
        suitable_roles = []

        try:
            # Get all policies
            all_policies = self.enforcer.get_policy()

            for policy in all_policies:
                if len(policy) >= 4:
                    policy_subject, policy_resource, policy_action, policy_scope = policy[:4]
                    policy_effect = policy[4] if len(policy) > 4 else "allow"

                    # Check if matches required permissions
                    if (
                        policy_resource == resource
                        and policy_action == action
                        and (policy_scope == "*" or policy_scope == scope)
                        and policy_effect == "allow"
                    ):
                        # Check if it's a role (not a specific user)
                        if policy_subject in [
                            "free_user",
                            "premium_user",
                            "enterprise_user",
                            "admin",
                            "viewer",
                            "editor",
                        ]:
                            suitable_roles.append(policy_subject)

            return list(set(suitable_roles))  # Remove duplicates

        except Exception as e:
            logger.error(f"Error finding suitable roles: {e}")
            return []

    def print_debug_info(self, debug_info: dict) -> None:
        """Print formatted debug information"""
        print("🔍 Permission Debug Report")
        print("=" * 50)

        # Request information
        req = debug_info["request"]
        print("\n📋 Permission Request:")
        print(f"   User: {req['user_id']}")
        print(f"   Resource: {req['resource']}")
        print(f"   Action: {req['action']}")
        print(f"   Scope: {req['scope']}")

        # User information
        user_info = debug_info["user_info"]
        print("\n👤 User Information:")
        print(f"   Roles: {user_info.get('roles', [])}")
        print(f"   Direct permissions: {len(user_info.get('direct_permissions', []))} items")

        # Permission check results
        check = debug_info["permission_check"]
        print("\n🔒 Permission Check:")
        print(f"   Casbin result: {'✅ Passed' if check['casbin_result'] else '❌ Denied'}")
        print(f"   Temporary permission: {'✅ Passed' if check['temporary_permission'] else '❌ Denied'}")
        print(f"   Final result: {'✅ Allowed' if check['final_result'] else '❌ Denied'}")

        # Matching policies
        policies = debug_info.get("matching_policies", [])
        print(f"\n📜 Matching policies: {len(policies)} items")
        for policy in policies:
            print(
                f"   • {policy['subject']} -> {policy['resource']}:{policy['action']}:{policy['scope']} ({policy['effect']})"
            )

        # Diagnosis information
        diagnosis = debug_info.get("diagnosis", [])
        if diagnosis:
            print("\n🔍 Diagnosis Information:")
            for diag in diagnosis:
                print(f"   {diag}")

        # Suggestions
        suggestions = debug_info.get("suggestions", [])
        if suggestions:
            print("\n💡 Suggestions:")
            for suggestion in suggestions:
                print(f"   {suggestion}")

        print("\n" + "=" * 50)

    def get_system_health(self) -> dict[str, Any]:
        """Get authorization system health status"""
        try:
            health_info: dict[str, Any] = {
                "status": "healthy",
                "components": {},
                "statistics": {},
                "issues": [],
            }

            # Check Casbin enforcer
            try:
                policy_count = len(self.enforcer.get_policy())
                health_info["components"]["casbin"] = {
                    "status": "healthy",
                    "policy_count": policy_count,
                }
            except Exception as e:
                health_info["components"]["casbin"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_info["issues"].append(f"Casbin enforcer error: {e}")

            # Check role configuration
            try:
                role_count = len(DEFAULT_ROLES)
                health_info["components"]["roles"] = {
                    "status": "healthy",
                    "role_count": role_count,
                    "available_roles": list(DEFAULT_ROLES.keys()),
                }
            except Exception as e:
                health_info["components"]["roles"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_info["issues"].append(f"Role configuration error: {e}")

            # Check cache status
            try:
                if self.permission_engine.cache:
                    cache_stats = self.permission_engine.cache.get_stats()
                    health_info["components"]["cache"] = {
                        "status": "healthy",
                        "enabled": True,
                        "stats": cache_stats,
                    }
                else:
                    health_info["components"]["cache"] = {
                        "status": "disabled",
                        "enabled": False,
                    }
            except Exception as e:
                health_info["components"]["cache"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_info["issues"].append(f"Cache system error: {e}")

            # Check audit system
            try:
                if self.permission_engine.audit_logger:
                    health_info["components"]["audit"] = {
                        "status": "healthy",
                        "enabled": True,
                    }
                else:
                    health_info["components"]["audit"] = {
                        "status": "disabled",
                        "enabled": False,
                    }
            except Exception as e:
                health_info["components"]["audit"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_info["issues"].append(f"Audit system error: {e}")

            # Overall status
            if health_info["issues"]:
                health_info["status"] = "degraded" if len(health_info["issues"]) < 3 else "unhealthy"

            return health_info

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "error",
                "error": str(e),
                "components": {},
                "statistics": {},
                "issues": [f"Health check failed: {e}"],
            }

    def validate_configuration(self) -> dict[str, Any]:
        """Validate authorization system configuration"""
        validation_result: dict[str, Any] = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
        }

        try:
            # Check role definitions
            for role_name, role_config in DEFAULT_ROLES.items():
                if not isinstance(role_config, dict):
                    validation_result["errors"].append(f"Role {role_name} configuration is not a dictionary")  # type: ignore[unreachable]
                    continue

                if "description" not in role_config:
                    validation_result["warnings"].append(f"Role {role_name} missing description")

                if "permissions" not in role_config:
                    validation_result["errors"].append(f"Role {role_name} missing permissions")
                    continue

                # Check permissions format
                permissions = role_config["permissions"]
                if not isinstance(permissions, list):
                    validation_result["errors"].append(f"Role {role_name} permissions should be a list")

            # Check for duplicate permissions
            all_permissions = []
            for role_config in DEFAULT_ROLES.values():
                if isinstance(role_config, dict) and "permissions" in role_config:
                    for perm in role_config["permissions"]:  # type: ignore[attr-defined]
                        perm_str = f"{perm.resource}:{perm.action}:{perm.scope}"
                        all_permissions.append(perm_str)

            duplicate_perms = {perm for perm in all_permissions if all_permissions.count(perm) > 1}
            if duplicate_perms:
                validation_result["warnings"].append(f"Duplicate permissions found: {', '.join(duplicate_perms)}")

            # Check policy consistency
            try:
                policies = self.enforcer.get_policy()
                if not policies:
                    validation_result["warnings"].append("No policies loaded in Casbin enforcer")
                else:
                    validation_result["suggestions"].append(f"Loaded {len(policies)} policies")
            except Exception as e:
                validation_result["errors"].append(f"Cannot access Casbin policies: {e}")

            # Set overall validation status
            if validation_result["errors"]:
                validation_result["valid"] = False

            return validation_result

        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return {
                "valid": False,
                "errors": [f"Configuration validation failed: {e}"],
                "warnings": [],
                "suggestions": [],
            }
