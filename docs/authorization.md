# MCP Factory Authorization System

Enterprise-level permission management system based on Casbin, providing fine-grained access control for ManagedServer.

## 🎯 Features

- **Role-Based Access Control (RBAC)** - Supports role inheritance and complex permission models
- **Fine-grained Permission Management** - Resource-level permission control
- **Temporary Permission Support** - Supports time-limited temporary permission grants
- **Permission Change History** - Complete audit logs of permission changes
- **Multiple Management Methods** - Supports MCP client calls and server-side programmatic access

## 🚀 Quick Start

### Enable Authorization System

```python
from mcp_factory.server import ManagedServer

# Create server with authorization
server = ManagedServer(
    name="my-secure-server",
    authorization=True,  # Enable authorization system
    expose_management_tools=True  # Expose management tools
)

# Start server
await server.run()
```

### Data Storage Location

The authorization system automatically creates necessary files in the user data directory:

- **macOS/Linux**: `~/.mcp-factory/`
- **Windows**: `%APPDATA%/mcp-factory/`

Included files:
- `authz_policy.csv` - Casbin permission policies
- `authz_extended.db` - Extended permission database
- `audit.db` - Audit log database
- `audit.log` - Audit log file

**Custom Data Directory**:
```bash
# Customize via environment variable
export MCP_FACTORY_DATA_DIR="/custom/path"
```

### Manage Permissions via MCP Client

After enabling authorization, the server automatically registers the following management tools:

```bash
# View all users
get_all_users()

# Assign user role
assign_user_role(user_id="alice", role="premium_user", reason="Upgrade to premium user")

# Check permissions
debug_permission(user_id="alice", resource="tool", action="execute", scope="premium")

# View user permissions
view_user_permissions(user_id="alice")

# Revoke role
revoke_user_role(user_id="alice", role="premium_user", reason="Subscription expired")
```

## 📋 Permission Model

### Default Roles

| Role | Permission Scope | Description |
|------|------------------|-------------|
| `free_user` | Basic features | Free users, can access basic tools and resources |
| `premium_user` | Advanced features | Paid users, can access advanced tools and features |
| `enterprise_user` | Enterprise features | Enterprise users, can access all business features |
| `admin` | System management | Administrators, can manage users and permissions |

### Permission Structure

Permissions use a four-tuple model: `(user, resource, action, scope)`

- **user**: User ID
- **resource**: Resource type (`mcp`, `tool`, `resource`)
- **action**: Action type (`read`, `write`, `execute`, `admin`)
- **scope**: Permission scope (`*`, `basic`, `premium`, `enterprise`)

### Default Permission Rules

```
# Basic permissions
free_user, mcp, read, *
free_user, tool, execute, basic
free_user, resource, read, basic

# Advanced permissions
premium_user, tool, execute, premium
premium_user, resource, read, premium

# Enterprise permissions
enterprise_user, tool, execute, enterprise
enterprise_user, resource, read, enterprise

# Administrator permissions
admin, *, *, *
```

## 🛠️ Usage Methods

### Method 1: MCP Client Calls (Recommended)

This is the most commonly used method, calling management tools through MCP client:

```python
# Call in MCP client
await client.call_tool("assign_user_role", {
    "user_id": "alice",
    "role": "premium_user",
    "reason": "User purchased premium package"
})

# Check permissions
result = await client.call_tool("debug_permission", {
    "user_id": "alice",
    "resource": "tool",
    "action": "execute", 
    "scope": "premium"
})
```

### Method 2: Server-side Programmatic Access

Direct access to authorization manager in server code (advanced usage):

```python
from mcp_factory.server import ManagedServer

async def setup_server():
    server = ManagedServer(name="my-server", authorization=True)
    
    # Use public authorization API (recommended)
    # Assign role
    success = server.assign_role(
        user_id="alice",
        role="premium_user", 
        assigned_by="system",
        reason="Auto upgrade"
    )
    
    # Check permissions
    can_execute = server.check_permission(
        user_id="alice",
        resource="tool",
        action="execute",
        scope="premium"
    )
    
    print(f"Role assignment successful: {success}")
    print(f"Alice can execute advanced tools: {can_execute}")
    
    # Advanced usage: direct access to authorization manager
    if server.authz:
        stats = server.authz.get_authorization_stats()
        print(f"System statistics: {stats}")
    
    return server
```

## 📚 Practical Examples

### Example 1: User Role Management

```python
from mcp_factory.server import ManagedServer

async def user_role_management():
    server = ManagedServer(name="role-demo", authorization=True)
    
    if server._authorization_manager:
        auth = server._authorization_manager
        
        # New user registration (default to free user)
        auth.assign_role("bob", "free_user", "system", "New user registration")
        
        # User upgrades to premium
        auth.assign_role("bob", "premium_user", "admin", "User purchased premium package")
        
        # Check user permissions
        can_use_premium = auth.check_permission("bob", "tool", "execute", "premium")
        print(f"Bob can use premium tools: {can_use_premium}")  # True
        
        # View all user roles
        roles = auth.get_user_roles("bob")
        print(f"Bob's roles: {roles}")  # ['free_user', 'premium_user']
    
    return server
```

### Example 2: Temporary Permission Management

```python
from datetime import datetime, timedelta
from mcp_factory.server import ManagedServer

async def temporary_permissions():
    server = ManagedServer(name='temp-demo", authorization=True)
    
    if server._authorization_manager:
        auth = server._authorization_manager
        
        # Grant user temporary enterprise-level permissions (2 hours)
        expires_at = datetime.now() + timedelta(hours=2)
        
        success = auth.grant_temporary_permission(
            user_id="charlie",
            resource="tool",
            action="execute", 
            scope="enterprise",
            expires_at=expires_at,
            granted_by="admin"
        )
        
        if success:
            # Check temporary permissions
            can_use_enterprise = auth.check_permission("charlie", "tool", "execute", "enterprise")
            print(f"Charlie has temporary enterprise permissions: {can_use_enterprise}")  # True
            
            # View temporary permission details
            temp_perms = auth.get_temporary_permissions("charlie")
            print(f"Charlie's temporary permissions: {temp_perms}")
    
    return server
```

### Example 3: Permission Check and Validation

```python
from mcp_factory.server import ManagedServer

async def permission_validation():
    server = ManagedServer(name="validation-demo", authorization=True)
    
    if server._authorization_manager:
        auth = server._authorization_manager
        
        # Set up test user
        auth.assign_role("david", "premium_user", "system", "Test user")
        
        # Batch permission checks
        permissions_to_check = [
            ("tool", "execute", "basic"),    # Should pass
            ("tool", "execute", "premium"),  # Should pass
            ("tool", "execute", "enterprise"), # Should fail
            ("mcp", "admin", "*")            # Should fail
        ]
        
        for resource, action, scope in permissions_to_check:
            result = auth.check_permission("david", resource, action, scope)
            print(f"David {resource}:{action}:{scope} = {result}")
        
        # Get user permission summary
        summary = auth.get_user_permission_summary("david")
        print(f"David's permission summary: {summary}")
    
    return server
```

## 🔧 Management Tools Details

### User Management Tools

| Tool Name | Function | Parameters |
|----------|------|------|
| `get_all_users` | Get all users list | None |
| `assign_user_role` | Assign user role | `user_id`, `role`, `reason` |
| `revoke_user_role` | Revoke user role | `user_id`, `role`, `reason` |
| `view_user_permissions` | View user permissions | `user_id` |

### Permission Debug Tools

| Tool Name | Function | Parameters |
|----------|------|------|
| `debug_permission` | Check specific permission | `user_id`, `resource`, `action`, `scope` |
| `get_permission_history` | Get permission change history | `user_id`, `limit` |

### System Management Tools

| Tool Name | Function | Parameters |
|----------|------|------|
| `get_authorization_stats` | Get authorization system statistics | None |
| `cleanup_expired_permissions` | Clean up expired permissions | None |

## 🎯 Best Practices

### 1. Role Design Principles

- **Principle of Least Privilege**: Users only receive the minimum permissions needed to complete their tasks
- **Role Inheritance**: Higher-level roles automatically include permissions from lower-level roles
- **Temporary Permissions**: Use temporary permissions for short-term needs rather than permanent role changes

### 2. Permission Management Process

```python
# Recommended permission management flow
async def recommended_permission_flow():
    server = ManagedServer(name="best-practice", authorization=True)
    
    if server._authorization_manager:
        auth = server._authorization_manager
        
        # 1. New users get minimum permissions by default
        auth.assign_role("new_user", "free_user", "system", "New user registration")
        
        # 2. Upgrade based on business needs
        # User purchase -> premium_user
        # Enterprise customer -> enterprise_user
        # Admin needs -> admin (grant carefully)
        
        # 3. Use temporary permissions for special cases
        # Rather than permanently elevating permission levels
        
        # 4. Regular auditing and cleanup
        # Use get_authorization_stats for monitoring
        # Use cleanup_expired_permissions for cleanup
```

### 3. Security Considerations

- **Administrator Permissions**: Grant `admin` role carefully, regularly review administrator list
- **Permission Auditing**: Regularly check permission change history to identify anomalous operations
- **Temporary Permissions**: Prioritize temporary permissions to avoid permission accumulation
- **Minimal Exposure**: Only enable `expose_management_tools` when needed

## 🔍 Troubleshooting

### Common Issues

**Q: User cannot access a tool**
```python
# Check user permissions
result = auth.check_permission(user_id, "tool", "execute", "premium")
if not result:
    # Check user roles
    roles = auth.get_user_roles(user_id)
    print(f"User roles: {roles}")
    
    # View permission history
    history = auth.get_permission_history(user_id)
    print(f"Permission history: {history}")
```

**Q: Temporary permissions not working**
```python
# Check temporary permission status
temp_perms = auth.get_temporary_permissions(user_id)
for perm in temp_perms:
    if perm["expires_at'] < datetime.now():
        print(f"Permission expired: {perm}")
```

**Q: Permission check failed**
```python
# Enable verbose logging
import logging
logging.getLogger('mcp_factory.authorization').setLevel(logging.DEBUG)

# Check permission rules
result = auth.check_permission(user_id, resource, action, scope)
print(f'Permission check result: {result}')
```

## 📖 Related Documentation

- [Configuration Guide](configuration.md) - Server configuration options
- [Middleware Documentation](middleware.md) - Custom permission middleware
- [CLI Guide](cli_guide.md) - Command line tool usage

## 🎯 Role System

MCP Factory provides a simplified three-tier role system designed for commercial applications:

### Core Roles

- **visitor** - Free/trial users with basic access permissions
- **user** - Paid users with full feature access (supports extended tiers)
- **admin** - System administrators with complete control

### UserTier Extension Mechanism

For applications requiring differentiated pricing, you can use UserTier to provide different permissions and limits for the `user` role:

```python
from mcp_factory.authorization.models import UserTier, MCPPermission

# Create different user tiers
basic_tier = UserTier(
    tier_id="basic",
    name="Basic Plan",
    price=9.0,
    additional_permissions=[...],
    limitation_overrides={...}
)
```

### Detailed Guide

For complete usage guide of the role system, see:
- [Role System Guide](role_system.md) - Detailed documentation on the three-tier role system

## 🔄 Version Compatibility

- **MCP Factory >= 1.0.0**: Full feature support
- **Casbin >= 1.0.0**: Permission engine dependency
- **Python >= 3.8**: Minimum Python version requirement

# New Role System Guide

MCP Factory's new three-tier role system provides a simple yet powerful permission management mechanism, perfectly balancing technical architecture simplicity with business model flexibility.

## 🎯 Core Concepts

### Three-Tier Role Architecture

MCP Factory provides three predefined core roles:

```python
DEFAULT_ROLES = {
    "visitor": {
        "description": "Free/trial users - basic access permissions",
        "base_permissions": [
            MCPPermission("mcp", "read", "info", "View basic server information"),
            MCPPermission("mcp", "read", "capabilities", "View server capabilities"),
        ],
        "default_limitations": {
            "daily_requests": 50,
            "max_tokens_per_request": 500,
            "rate_limit_per_minute": 5,
            "trial_duration_days": 7
        },
        "extensible": True
    },
    
    "user": {
        "description": "Paid users - full access permissions, supports extended tiers",
        "base_permissions": [
            MCPPermission("mcp", "read", "info", "View basic server information"),
            MCPPermission("mcp", "read", "capabilities", "View server capabilities"),
            MCPPermission("mcp", "read", "status", "View server status"),
        ],
        "default_limitations": {
            "daily_requests": 1000,
            "max_tokens_per_request": 4000,
            "rate_limit_per_minute": 60
        },
        "extensible": True
    },
    
    "admin": {
        "description": "Administrator - full access permissions",
        "base_permissions": [
            # Includes all MCP permissions + admin permissions
        ],
        "default_limitations": {},  # No limits
        "extensible": True
    }
}
```

### Key Design Principles

1. **Roles are fixed** - Developers don't need to create roles, just use these three predefined ones
2. **Plans are flexible** - Developers can freely design business plans
3. **Mapping connects them** - Establish associations between business plans and technical roles through `billing_role_mapping`
4. **UserTier handles differences** - Provides differentiated features for different plans under the same role

## 🚀 Development Workflow

### Step 1: Design Business Plans

```python
# Developers design paid plans based on business needs
plans = ["free", "basic", "pro", "enterprise"]
```

### Step 2: Establish Plan to Role Mapping

```python
billing_role_mapping = {
    "free": "visitor",        # free plan → visitor role
    "basic": "user",          # paid plan → user role
    "pro": "user",            # premium plan → user role
    "enterprise": "user"      # enterprise plan → user role
}
```

### Step 3: Configure Application-Specific Permissions

```python
from mcp_factory.authorization.models import configure_role_permissions, MCPPermission

# Add application-specific permissions for visitor role
configure_role_permissions("visitor", [
    MCPPermission("ai", "access", "gpt35", "Access GPT-3.5"),
    MCPPermission("file", "read", "demo", "Read demo files")
])

# Add application-specific permissions for user role
configure_role_permissions("user", [
    MCPPermission("ai", "access", "gpt4", "Access GPT-4"),
    MCPPermission("file", "write", "personal", "Write personal files"),
    MCPPermission("api", "access", "standard", "Standard API access")
])
```

### Step 4: Configure Custom Limitations

```python
from mcp_factory.authorization.models import configure_role_limitations

# Configure limitations for visitor role
configure_role_limitations("visitor", {
    "daily_requests": 10,
    "max_file_size": 1,
    "allowed_models": ["gpt-3.5-turbo"]
})

# Configure limitations for user role
configure_role_limitations("user", {
    "daily_requests": 500,
    "max_file_size": 100,
    "allowed_models": ["gpt-3.5-turbo", "gpt-4"]
})
```

### Step 5: Create UserTier (Optional)

To provide differentiated features for different paid plans:

```python
from mcp_factory.authorization.models import UserTier

# Basic Plan
basic_tier = UserTier(
    tier_id="basic",
    name="Basic Plan",
    description="Basic AI assistant features",
    price=9.0,
    additional_permissions=[
        MCPPermission("ai", "access", "gpt4", "Access GPT-4"),
    ],
    limitation_overrides={
        "daily_requests": 100,
        "max_tokens_per_request": 2000
    }
)

# Pro Plan
pro_tier = UserTier(
    tier_id="pro",
    name="Pro Plan",
    description="Professional AI assistant features",
    price=29.0,
    additional_permissions=[
        MCPPermission("ai", "access", "gpt4", "Access GPT-4"),
        MCPPermission("ai", "access", "claude", "Access Claude"),
        MCPPermission("api", "access", "standard", "API access")
    ],
    limitation_overrides={
        "daily_requests": 1000,
        "max_tokens_per_request": 8000
    }
)
```

### Step 6: Configure Integration

```python
from mcp_factory.server.billing_auth_integration import BillingAuthIntegration

# Configure plan mapping
custom_plan_config = {
    "billing_role_mapping": {
        "free": "visitor",
        "basic": "user",
        "pro": "user",
        "enterprise": "user"
    },
    "user_tier_mapping": {
        "basic": "basic",      # basic plan uses basic_tier
        "pro": "pro",          # pro plan uses pro_tier
        "enterprise": "pro"    # enterprise reuses pro_tier
    },
    "plan_upgrade_path": {
        "free": "basic",
        "basic": "pro",
        "pro": "enterprise"
    }
}

# Initialize integration
integration = BillingAuthIntegration(
    billing_system=billing,
    authorization_manager=auth,
    plan_config=custom_plan_config
)
```

## 💡 Usage Examples

### Permission Check

```python
# Check user permissions
result = integration.check_permission_with_upgrade_suggestions(
    user_id="user123",
    resource="ai",
    action="access",
    scope="gpt4"
)

if result["allowed"]:
    # Execute operation
    response = await call_ai_model("gpt4")
else:
    # Return error and upgrade suggestion
    return {
        "error": result["reason"],
        "upgrade_suggestion": result["upgrade_suggestion"],
        "required_plan": result["required_plan"]
    }
```

### Get User Information

```python
# Get user role and plan information
role_info = integration.get_user_role_info("user123")
print(f"User role: {role_info['role']}")
print(f"paid plan: {role_info['plan']}")
print(f"User tier: {role_info['tier']}")
```

### Dynamic Plan Management

```python
# Add new plan
integration.add_plan("premium", "user", "pro")

# Remove plan
integration.remove_plan("old_plan")

# Get current configuration
config = integration.get_plan_config()
```

## 🎯 Best Practices

### 1. Start from Business Requirements

- First analyze target user groups and willingness to pay
- Design paid plans with differentiated value
- Distribute features to different plans based on value

### 2. Keep Role System Simple

- Use fixed three-tier roles
- Handle complex business requirements through configuration
- Avoid creating too many custom roles

### 3. Use UserTier Appropriately

- Only use when different paid plans require differentiation
- Provide fine-grained control for different plans under the same role
- Keep the number of UserTiers reasonable

### 4. Permission Design Principles

- `base_permissions` only includes common MCP protocol permissions
- Application-specific permissions are added via `configure_role_permissions`
- Use clear permission naming: `resource:action:scope`

### 5. Limitation Configuration Strategy

- Set reasonable usage limits for different roles
- Guide users to upgrade through limitations
- Consider user experience, avoid overly strict limitations

## 🔄 Data Flow

```
User purchases "pro" plan
↓
billing_role_mapping["pro"] → "user" role
↓
user_tier_mapping["pro"] → pro_tier
↓
user role base_permissions + pro_tier additional_permissions
↓
user role default_limitations + pro_tier limitation_overrides
↓
Final permissions and limitations
```

## 🎊 Summary of Advantages

### Value for Developers

- **Simplified development** - No need to understand complex permission logic
- **Business alignment** - Technical implementation directly maps to business model
- **User experience** - Automatic upgrade suggestions improve conversion rate
- **Easy maintenance** - Configuration-based permission management
- **Easy to extend** - New features can quickly integrate permission control

### System Architecture Advantages

- **Simplicity** - Only three core roles, easy to understand and maintain
- **Flexibility** - Supports complex business models and pricing strategies
- **Extensibility** - Can easily add new plans and features
- **Consistency** - All MCP servers use the same role system

## 📚 Related Documentation

- [UserTier Creation Example](../../examples/user_tier_creation_demo.py)
- [Authorization System](README.md) - Complete authorization system documentation
- [Configuration Guide](../configuration.md) - System configuration options
- [Architecture Documentation](../architecture/) - System architecture design

---

**Remember: Roles are fixed technical architecture, plans are flexible business design!** 🎯
