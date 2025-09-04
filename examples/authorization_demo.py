"""
MCP Factory Authorization Complete Demo

Complete demonstration of mcp-factory's authorization management system, from basic configuration to advanced features

📋 Demo Content:
1. Quick Start - authorization parameter configuration and basic concepts
2. Basic Permission Management - role assignment, permission check, user management
3. Advanced Features - temporary permissions, management tool calls, audit logs
4. Business Scenarios - SaaS permission requests and approval workflows
5. Best Practices - configuration comparison, design principles, troubleshooting

🎯 Use Cases:
- Complete understanding of MCP Factory authorization system
- Complete learning path from configuration to usage
- Production environment permission management reference
"""

import asyncio
import logging
from datetime import datetime, timedelta

from mcp_factory.server import ManagedServer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Part 1: Quick Start - Basic Configuration and Concepts
# ============================================================================


def demo_basic_configuration():
    """Demonstrate basic configuration options"""

    print("🎯 Part 1: Authorization Parameter Configuration")
    print("=" * 50)

    print("\n1. Default Behavior (authorization=None)")
    print("   - Auto-infer based on auth parameter")
    print("   - No auth -> Disable authorization")
    print("   - Has auth -> Enable authorization")

    # Default behavior
    server1 = ManagedServer(name="auto-server")
    print(f"   server1.authorization: {server1.authorization}")

    print("\n2. Explicitly Enable (authorization=True)")
    print("   - Force enable authorization check")
    print("   - Use Casbin RBAC system")

    server2 = ManagedServer(name="secure-server", authorization=True)
    print(f"   server2.authorization: {server2.authorization}")

    print("\n3. Explicitly Disable (authorization=False)")
    print("   - Force disable authorization check")
    print("   - All operations are allowed")

    server3 = ManagedServer(name="open-server", authorization=False)
    print(f"   server3.authorization: {server3.authorization}")


def demo_with_authentication():
    """Demonstrate integration with authentication system"""

    print("\n🔐 Integration with Authentication System")
    print("=" * 30)

    try:
        from fastmcp.server.auth.providers.jwt import JWTVerifier, RSAKeyPair

        print("\n1. JWT authentication + Auto-infer authorization")
        key_pair = RSAKeyPair.generate()
        jwt_auth = JWTVerifier(public_key=key_pair.public_key)

        server_jwt = ManagedServer(
            name="jwt-server",
            auth=jwt_auth,  # authorization=None will auto-enable
        )
        print(f"   JWT server authorization: {server_jwt.authorization}")

        print("\n2. JWT authentication + Explicitly disable authorization")
        server_jwt_open = ManagedServer(
            name="jwt-open-server",
            auth=jwt_auth,
            authorization=False,  # Explicitly disable
        )
        print(f"   JWT open server authorization: {server_jwt_open.authorization}")

    except ImportError:
        print("   ⚠️ FastMCP JWT provider not available")

    print("\n3. No authentication + Explicitly enable authorization")
    server_no_auth = ManagedServer(
        name="no-auth-secure-server",
        auth=None,
        authorization=True,  # Enable authorization even without authentication
    )
    print(f"   No auth secure server authorization: {server_no_auth.authorization}")


def demo_configuration_comparison():
    """Demonstrate configuration comparison table"""

    print("\n📊 Configuration Options Comparison")
    print("=" * 25)

    configs = [
        ("default", {}, "auto-infer"),
        ("Explicitly Enable", {"authorization": True}, "enabled"),
        ("Explicitly Disable", {"authorization": False}, "disabled"),
        ("With Authentication", {"auth": "JWTVerifier(...)"}, "auto-enabled"),
        ("No Authentication", {"auth": None}, "auto-disabled"),
    ]

    print(f"{'configuration':<12} {'Parameters':<30} {'Authorization Status':<20}")
    print("-" * 65)

    for name, config, status in configs:
        config_str = str(config) if config else "Default"
        if len(config_str) > 28:
            config_str = config_str[:25] + "..."
        print(f"{name:<12} {config_str:<30} {status:<20}")


# ============================================================================
# Part 2: Basic Permission Management
# ============================================================================


async def demo_basic_authorization():
    """Demonstrate basic permission management functions"""

    print("\n\n🛡️ Part 2: Basic Permission Management")
    print("=" * 40)

    # 1. Create server with authorization
    print("\n1. Create ManagedServer with Authorization...")

    server = ManagedServer(name="authorization-demo-server", authorization=True, expose_management_tools=True)

    # 2. Create initial admin user
    print("\n2. Create initial admin user...")
    admin_created = server.create_admin_user("admin_user", "Demo initialization")
    print(f"   Admin created: {'✅ Success' if admin_created else '❌ Failed'}")

    # 3. Display authorization system status
    print("\n3. Authorization system status:")
    if server.authz:
        try:
            stats = server.authz.get_authorization_stats()
            print(f"   Total users: {stats.get('total_users', 0)}")
            print(f"   Total roles: {stats.get('total_roles', 0)}")
            print(f"   Total permissions: {stats.get('total_permissions', 0)}")
        except Exception as e:
            print(f"   Status retrieval failed: {e}")
    else:
        print("   ❌ Authorization system not enabled")

    # 4. Demonstrate role management
    print("\n4. Demonstrate role management...")

    # Simulate admin operations (assign roles)
    test_users = [
        ("user_alice", "premium_user", "Paid user"),
        ("user_bob", "free_user", "Free user"),
        ("user_charlie", "enterprise_user", "Enterprise user"),
    ]

    for user_id, role, description in test_users:
        success = server.assign_role(user_id, role, "admin_user", description)
        print(f"   {user_id} -> {role}: {'✅' if success else '❌'}")

    # 5. Demonstrate permission checks
    print("\n5. Demonstrate permission checks...")

    permission_tests = [
        ("user_alice", "tool", "execute", "premium"),
        ("user_bob", "tool", "execute", "premium"),
        ("user_charlie", "tool", "execute", "enterprise"),
        ("user_bob", "mcp", "read", "*"),
    ]

    for user_id, resource, action, scope in permission_tests:
        has_permission = server.check_permission(user_id, resource, action, scope)
        print(f"   {user_id} {resource}:{action}:{scope} = {'✅' if has_permission else '❌'}")

    return server


# ============================================================================
# Part 3: Advanced Features
# ============================================================================


async def demo_advanced_features(server):
    """Demonstrate advanced features"""

    print("\n\n⚡ Part 3: Advanced Features")
    print("=" * 30)

    if not server.authz:
        print("❌ Authorization manager not available")
        return

    # 1. Temporary permission management
    print("\n1. Temporary permission management...")

    expires_at = datetime.now() + timedelta(minutes=30)
    temp_granted = server.authz.grant_temporary_permission(
        "user_bob", "tool", "execute", "premium", expires_at, "admin_user"
    )
    print(f"   Temporary permission granted: {'✅ Success' if temp_granted else '❌ Failed'}")

    if temp_granted:
        # Check temporary permissions
        has_temp_permission = server.check_permission("user_bob", "tool", "execute", "premium")
        print(f"   Bob can now use advanced tools: {'✅' if has_temp_permission else '❌'}")

    # 2. Permission history tracking
    print("\n2. Permission history tracking...")

    for user_id in ["user_alice", "user_bob"]:
        try:
            history = server.authz.get_permission_history(user_id, 3)
            print(f"   {user_id} recent permission changes: {len(history)} records")
            for record in history[:2]:  # Only show first 2 records
                print(f"     - {record.get('action', 'unknown')} at {record.get('timestamp', 'unknown')}")
        except Exception as e:
            print(f"   {user_id} history retrieval failed: {e}")

    # 3. View effective permissions
    print("\n3. View effective permissions...")

    for user_id in ["user_alice", "user_bob"]:
        try:
            permissions = server.authz.get_effective_permissions(user_id)
            print(f"   {user_id} effective permissions: {len(permissions)} items")
        except Exception as e:
            print(f"   {user_id} permission retrieval failed: {e}")

    # 4. Role information
    print("\n4. System role information...")

    try:
        available_roles = server.authz.get_available_roles()
        print(f"   Available roles: {', '.join(available_roles)}")
    except Exception as e:
        print(f"   Role information retrieval failed: {e}")


# ============================================================================
# Part 4: Management Tools Demo
# ============================================================================


async def demo_management_tools():
    """Demonstrate usage of management tools"""

    print("\n\n🛠️ Part 4: Management Tools Demo")
    print("=" * 35)

    server = ManagedServer(name="management-tools-demo", authorization=True, expose_management_tools=True)

    # Create demo admin
    server.create_admin_user("demo_admin", "Demo admin")

    # Simulate management tool calls
    print("\nAvailable authorization management tools:")

    management_tools = [
        "get_all_users",
        "assign_user_role",
        "revoke_user_role",
        "view_user_permissions",
        "debug_permission",
        "get_permission_history",
        "get_authorization_stats",
        "cleanup_expired_permissions",
    ]

    for tool in management_tools:
        print(f"   🛠️ {tool}")

    print("\nManagement tool call examples:")
    print("   # Call via MCP client")
    print("   await client.call_tool('assign_user_role', {")
    print("       'user_id': 'alice',")
    print("       'role': 'premium_user',")
    print("       'reason': 'User purchased premium package'")
    print("   })")

    return server


# ============================================================================
# Part 5: Business Scenario Demo
# ============================================================================


def demo_business_scenarios():
    """Demonstrate business scenarios"""

    print("\n\n💼 Part 5: Business Scenario Demo")
    print("=" * 35)

    print("\n1. SaaS Permission Request Process")
    print("   Step 1: User registration -> assign free_user role")
    print("   Step 2: User requests upgrade -> create request record")
    print("   Step 3: Admin approval -> upgrade to premium_user")
    print("   Step 4: Payment confirmation -> activate advanced features")

    print("\n2. Enterprise Permission Management")
    print("   Scenario 1: New employee onboarding -> assign basic roles")
    print("   Scenario 2: Project needs -> temporary permission grant")
    print("   Scenario 3: Employee departure -> revoke all permissions")

    print("\n3. Permission Auditing")
    print("   Regular checks: expired permission cleanup")
    print("   Security audit: permission change history")
    print("   Compliance requirements: permission usage statistics")


# ============================================================================
# Part 6: Best Practices and Troubleshooting
# ============================================================================


def demo_best_practices():
    """Demonstrate best practices"""

    print("\n\n✅ Part 6: Best Practices")
    print("=" * 30)

    print("\n1. Configuration Best Practices")
    print("   ✅ Production environment: authorization=True")
    print("   ✅ Development environment: authorization=False (optional)")
    print("   ✅ Test environment: authorization=True (recommended)")

    print("\n2. Permission Design Principles")
    print("   ✅ Principle of least privilege: only grant necessary permissions")
    print("   ✅ Role inheritance: higher roles include lower-level permissions")
    print("   ✅ Temporary permissions: use temporary permissions for short-term needs")

    print("\n3. Security Considerations")
    print("   ⚠️ Admin permissions: carefully grant admin role")
    print("   ⚠️ Permission auditing: regularly check permission changes")
    print("   ⚠️ Expiration cleanup: timely cleanup of expired permissions")

    print("\n4. Performance Optimization")
    print("   🚀 Permission caching: automatically cache permission check results")
    print("   🚀 Batch operations: use batch APIs to reduce database access")
    print("   🚀 Index optimization: establish appropriate indexes on permission tables")


def demo_troubleshooting():
    """Demonstrate troubleshooting"""

    print("\n\n🔍 Troubleshooting Guide")
    print("=" * 25)

    print("\nCommon Issues and Solutions:")

    print("\n❓ Issue 1: User cannot access a tool")
    print("   🔧 Check user roles: get_user_roles(user_id)")
    print("   🔧 Check permissions: debug_permission(user_id, resource, action, scope)")
    print("   🔧 View history: get_permission_history(user_id)")

    print("\n❓ Issue 2: Temporary permissions not working")
    print("   🔧 Check expiration time: get_temporary_permissions(user_id)")
    print("   🔧 Clean expired permissions: cleanup_expired_permissions()")
    print("   🔧 Check system time: ensure server time is correct")

    print("\n❓ Issue 3: Permission check failed")
    print("   🔧 Enable debug logging: logging.getLogger('mcp_factory.authorization').setLevel(DEBUG)")
    print("   🔧 Check permission rules: confirm RBAC model configuration is correct")
    print("   🔧 Database connection: check Casbin Database connection")


# ============================================================================
# Main Demo Function
# ============================================================================


async def main():
    """Main demo function"""

    print("🚀 MCP Factory Authorization Complete Demo")
    print("=" * 55)
    print("Complete demonstration of authorization management system from configuration to usage")

    # Part 1: Quick Start
    demo_basic_configuration()
    demo_with_authentication()
    demo_configuration_comparison()

    # Part 2: Basic Permission Management
    server = await demo_basic_authorization()

    if server:
        # Part 3: Advanced Features
        await demo_advanced_features(server)

        # Part 4: Management Tools
        await demo_management_tools()

    # Part 5: Business Scenarios
    demo_business_scenarios()

    # Part 6: Best Practices
    demo_best_practices()
    demo_troubleshooting()

    print("\n" + "=" * 55)
    print("✅ Demo completed!")
    print("\n📚 Related Documentation:")
    print("  • docs/authorization.md - Detailed usage guide")
    print("  • docs/configuration.md - Configuration options")
    print("  • docs/cli_guide.md - Command line tools")

    print("\n🎯 Next Steps:")
    print("  • Enable authorization=True in your project")
    print("  • Design roles and permissions based on business needs")
    print("  • Use management tools for permission management")
    print("  • Regularly conduct permission auditing and cleanup")


if __name__ == "__main__":
    asyncio.run(main())
