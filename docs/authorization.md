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

# 检查权限
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
        
        # 新用户注册（默认为免费用户）
        auth.assign_role("bob", "free_user", "system", "新用户注册")
        
        # 用户升级到高级版
        auth.assign_role("bob", "premium_user", "admin", "用户购买高级套餐")
        
        # 检查用户权限
        can_use_premium = auth.check_permission("bob", "tool", "execute", "premium")
        print(f"Bob 可以使用高级工具: {can_use_premium}")  # True
        
        # 查看用户所有角色
        roles = auth.get_user_roles("bob")
        print(f"Bob 的角色: {roles}")  # ['free_user', 'premium_user']
    
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
        
        # 给用户临时的企业级权限（2小时）
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
            # 检查临时权限
            can_use_enterprise = auth.check_permission("charlie", "tool", "execute", "enterprise")
            print(f"Charlie 有临时企业权限: {can_use_enterprise}")  # True
            
            # 查看临时权限详情
            temp_perms = auth.get_temporary_permissions("charlie")
            print(f"Charlie 的临时权限: {temp_perms}")
    
    return server
```

### Example 3: Permission Check and Validation

```python
from mcp_factory.server import ManagedServer

async def permission_validation():
    server = ManagedServer(name="validation-demo", authorization=True)
    
    if server._authorization_manager:
        auth = server._authorization_manager
        
        # 设置测试用户
        auth.assign_role("david", "premium_user", "system", "测试用户")
        
        # 批量权限检查
        permissions_to_check = [
            ("tool", "execute", "basic"),    # 应该通过
            ("tool", "execute", "premium"),  # 应该通过  
            ("tool", "execute", "enterprise"), # 应该 failed
            ("mcp", "admin", "*")            # 应该 failed
        ]
        
        for resource, action, scope in permissions_to_check:
            result = auth.check_permission("david", resource, action, scope)
            print(f"David {resource}:{action}:{scope} = {result}")
        
        # 获取用户权限摘要
        summary = auth.get_user_permission_summary("david")
        print(f"David 权限摘要: {summary}")
    
    return server
```

## 🔧 Management Tools Details

### User Management Tools

| Tool Name | Function | Parameters |
|----------|------|------|
| `get_all_users` | Get all users list | 无 |
| `assign_user_role` | Assign user role | `user_id`, `role`, `reason` |
| `revoke_user_role` | Revoke user role | `user_id`, `role`, `reason` |
| `view_user_permissions` | View user permissions | `user_id` |

### Permission Debug Tools

| Tool Name | Function | Parameters |
|----------|------|------|
| `debug_permission` | 检查特定权限 | `user_id`, `resource`, `action`, `scope` |
| `get_permission_history` | 获取权限变更历史 | `user_id`, `limit` |

### System Management Tools

| Tool Name | Function | Parameters |
|----------|------|------|
| `get_authorization_stats` | 获取授权系统统计 | 无 |
| `cleanup_expired_permissions` | 清理过期权限 | 无 |

## 🎯 Best Practices

### 1. Role Design Principles

- **最小权限原则**: 用户只获得完成任务所需的最小权限
- **角色继承**: 高级角色自动包含低级角色的权限
- **临时权限**: 对于短期需求使用临时权限而非永久角色变更

### 2. Permission Management Process

```python
# 推荐的权限管理流程
async def recommended_permission_flow():
    server = ManagedServer(name="best-practice", authorization=True)
    
    if server._authorization_manager:
        auth = server._authorization_manager
        
        # 1. 新用户默认最低权限
        auth.assign_role("new_user", "free_user", "system", "新用户注册")
        
        # 2. 根据业务需求升级
        # 用户购买 -> premium_user
        # 企业客户 -> enterprise_user
        # 管理需求 -> admin (谨慎授予)
        
        # 3. 使用临时权限处理特殊情况
        # 而不是永久提升权限级别
        
        # 4. 定期审计和清理
        # 使用 get_authorization_stats 监控
        # 使用 cleanup_expired_permissions 清理
```

### 3. Security Considerations

- **管理员权限**: 谨慎授予 `admin` 角色，定期审查管理员列表
- **权限审计**: 定期检查权限变更历史，发现异常操作
- **临时权限**: 优先使用临时权限，避免权限累积
- **最小暴露**: 只在需要时启用 `expose_management_tools`

## 🔍 Troubleshooting

### Common Issues

**Q: 用户无法访问某个工具**
```python
# 检查用户权限
result = auth.check_permission(user_id, "tool", "execute", "premium")
if not result:
    # 检查用户角色
    roles = auth.get_user_roles(user_id)
    print(f"用户角色: {roles}")
    
    # 查看权限历史
    history = auth.get_permission_history(user_id)
    print(f"权限历史: {history}")
```

**Q: 临时权限不生效**
```python
# 检查临时权限状态
temp_perms = auth.get_temporary_permissions(user_id)
for perm in temp_perms:
    if perm["expires_at'] < datetime.now():
        print(f"权限已过期: {perm}")
```

**Q: 权限检查失败**
```python
# 启用详细日志
import logging
logging.getLogger('mcp_factory.authorization').setLevel(logging.DEBUG)

# 检查权限规则
result = auth.check_permission(user_id, resource, action, scope)
print(f'权限检查结果: {result}')
```

## 📖 Related Documentation

- [配置指南](configuration.md) - 服务器配置选项
- [中间件文档](middleware.md) - 自定义权限中间件
- [CLI 指南](cli_guide.md) - 命令行工具使用

## 🔄 Version Compatibility

- **MCP Factory >= 1.0.0**: 完整功能支持
- **Casbin >= 1.0.0**: 权限引擎依赖
- **Python >= 3.8**: 最低 Python 版本要求