# Troubleshooting

This document contains common issues and solutions when using MCP Factory.

# # 🔧 Installation Issues

# ## Q: `mcpf` command not found

**Issue**: After installation, executing `mcpf` shows "command not found"

**Solutions**:
```bash
# Confirm installation success
pip list | grep mcp-factory

# Check PATH environment variable
which mcpf

# Use full module path
python -m mcp_factory.cli.main --help

# Reinstall
pip uninstall mcp-factory
pip install mcp-factory
```

# ## Q: Dependency conflicts

**Issue**: Dependency version conflicts during installation

**Solutions**:
```bash
# Use virtual environment
python -m venv mcp-env
source mcp-env/bin/activate  # Linux/Mac
# mcp-env\Scripts\activate   # Windows

# Use uv (recommended)
uv venv
source .venv/bin/activate
uv add mcp-factory
```

# # 🖥️ CLI Issues

# ## Q: Configuration file validation failed

**Issue**: `mcpf validate config.yaml` reports configuration errors

**Solutions**:
```bash
# View detailed error information
mcpf validate config.yaml --verbose

# Regenerate using official template
mcpf template --type simple > new-config.yaml

# Check common configuration errors:
# 1. YAML syntax errors (indentation, colons)
# 2. Missing required fields (name, instructions)
# 3. Port conflicts or out of range
```

# ## Q: Server startup failed

**Issue**: `mcpf run config.yaml` cannot start server

**Solutions**:
```bash
# Check if port is occupied
lsof -i :8888  # Replace with your port number

# Use different port
mcpf run config.yaml --port 9000

# Enable debug mode for detailed information
mcpf run config.yaml --debug

# Check host settings in configuration file
# Ensure host: "localhost" or host: "0.0.0.0"
```

# # 🔐 Authentication Issues

# ## Q: Auth0 authentication provider creation failed

**Issue**: `mcpf auth` command cannot create Auth0 provider

**Solutions**:
```bash
# Confirm required parameters
mcpf auth my-auth \
  --type auth0 \
  --domain your-tenant.auth0.com \
  --client-id "your-client-id" \
  --client-secret "your-client-secret"

# Check Auth0 configuration:
# 1. Domain format correct (xxx.auth0.com)
# 2. Client ID and Secret valid
# 3. Application type set to "Machine to Machine"
```

# ## Q: Authentication token validation failed

**Issue**: Client requests rejected with authentication failure

**Solutions**:
```bash
# Check token format
curl -H "Authorization: Bearer your-token" \
     http://localhost:8888/api/mcp

# Verify Auth0 configuration
# 1. audience set correctly
# 2. roles_namespace matches
# 3. Token not expired
```

# # 🚀 Server Runtime Issues

# ## Q: Tools cannot be called

**Issue**: Client cannot call server tools

**Solutions**:
```bash
# Check if tools are registered successfully
curl -X POST http://localhost:8888/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'

# Confirm tool configuration
# 1. expose_management_tools: true (if management tools needed)
# 2. Custom tools registered correctly
# 3. Tool parameter types match
```

# ## Q: Configuration hot reload failed

**Issue**: `manage_reload_config` tool reports error

**Solutions**:
```bash
# Confirm configuration file path is correct
# Confirm new configuration file syntax is correct
mcpf validate new-config.yaml

# Check permissions
# 1. File read permissions
# 2. User authentication permissions (if authentication enabled)
```

# # 📁 File and Path Issues

# ## Q: Configuration file not found

**Issue**: Specified configuration file path is invalid

**Solutions**:
```bash
# Use absolute path
mcpf run /full/path/to/config.yaml

# Check current directory
pwd
ls -la *.yaml

# Generate new configuration using template
mcpf template --type simple > config.yaml
```

# ## Q: Permission errors

**Issue**: Cannot read configuration file or create log files

**Solutions**:
```bash
# Check file permissions
ls -la config.yaml

# Modify permissions
chmod 644 config.yaml

# Check directory permissions
chmod 755 ~/.mcpf
```

# # 🌐 Network Issues

# ## Q: Client connection timeout

**Issue**: Client cannot connect to server

**Solutions**:
```bash
# Check if server is running
curl http://localhost:8888/api/mcp

# Check if port is open
netstat -tuln | grep 8888

# Check firewall settings
# 1. Local firewall
# 2. Network firewall
# 3. Cloud provider security groups
```

# ## Q: CORS cross-origin issues

**Issue**: Browser client reports CORS errors

**Solutions**:
Add CORS settings to configuration file:
```yaml
advanced:
  cors_origins: ["http://localhost:3000", "https://your-domain.com"]
  cors_methods: ["GET", "POST", "OPTIONS"]
  cors_headers: ["Content-Type", "Authorization"]
```

# # 📤 Publishing Issues

# ## Q: GitHub App installation failed

**Issue**: Cannot install GitHub App or installation process stuck

**Solutions**:
```bash
# Check GitHub App status
curl -I https://github.com/apps/mcp-project-manager

# Verify your GitHub permissions
# 1. Go to https://github.com/settings/installations
# 2. Check if you have permission to install Apps
# 3. Try refreshing the browser and retry

# Use manual publishing as fallback
mcpf project publish my-project --manual
```

# ## Q: Repository creation failed

**Issue**: Error "Repository already exists" or "Failed to create repository"

**Solutions**:
```bash
# Check if repository exists
curl -I https://api.github.com/repos/your-username/project-name

# Use different project name
mcpf project publish my-project-v2

# Delete existing repository and retry
# (Be careful - this will delete all data)
# 1. Go to GitHub repository settings
# 2. Delete repository
# 3. Retry publishing

# Force republish (overwrites existing)
mcpf project publish my-project --force
```

# ## Q: Authentication issues during publishing

**Issue**: "Permission denied" or "Invalid credentials" errors

**Solutions**:
```bash
# Check GitHub App installation status
curl "https://mcp-project-manager.vercel.app/api/installation-status?username=your-username"

# Reinstall GitHub App
# 1. Go to https://github.com/settings/installations
# 2. Uninstall "MCP Project Manager"
# 3. Reinstall from: https://github.com/apps/mcp-project-manager/installations/new

# Clear local authentication cache
rm -f ~/.mcpf/auth-cache.json

# Set GitHub token as fallback
export GITHUB_TOKEN="your-github-token"
mcpf project publish my-project
```

# ## Q: Project validation failed before publishing

**Issue**: Project doesn't meet publishing requirements

**Solutions**:
```bash
# Check project structure
mcpf project validate my-project

# Common requirements:
# 1. Must have pyproject.toml file
# 2. Must have README.md file
# 3. Must have valid MCP server structure
# 4. Must have Git repository initialized

# Fix missing files
cd my-project
touch README.md
git init
git add .
git commit -m "Initial commit"

# Validate configuration
mcpf config validate config.yaml
```

# ## Q: Network connection issues during publishing

**Issue**: Timeout or connection errors to GitHub services

**Solutions**:
```bash
# Check network connectivity
curl -I https://api.github.com
curl -I https://mcp-project-manager.vercel.app/api/health

# Use proxy if needed
export HTTPS_PROXY=http://your-proxy:port
mcpf project publish my-project

# Increase timeout
mcpf project publish my-project --timeout 120

# Try manual git operations
cd my-project
git remote add origin https://github.com/your-username/project-name.git
git push -u origin main
```

# ## Q: Hub registration failed

**Issue**: Project published to GitHub but not appearing in MCP Servers Hub

**Solutions**:
```bash
# Check webhook configuration
# 1. Go to your GitHub repository settings
# 2. Check "Webhooks" section
# 3. Verify webhook URL: https://mcp-project-manager.vercel.app/api/github/webhooks

# Manually trigger registration
curl -X POST https://mcp-project-manager.vercel.app/api/github/webhooks \
  -H "Content-Type: application/json" \
  -d '{"repository": {"full_name": "your-username/project-name"}}'

# Check Hub registry manually
curl -s "https://api.github.com/repos/ACNet-AI/mcp-servers-hub/contents/registry.json" | \
  jq '.content' | base64 -d | jq '.[] | select(.name == "your-project-name")'

# Wait for webhook processing (can take 1-5 minutes)
# Check project status
mcpf project status my-project
```

# # 📋 Common Debug Commands

```bash
# Check version
mcpf --version

# Verbose output
mcpf --verbose run config.yaml

# List all resources
mcpf list

# Validate configuration
mcpf validate config.yaml

# Generate minimal configuration for testing
mcpf template --type minimal | mcpf validate /dev/stdin
```

# # 🆘 Getting Help

If none of the above solutions work for your issue, please:

1. **Check logs**: Enable `--debug` mode to view detailed logs
2. **Search Issues**: [GitHub Issues](https://github.com/your-repo/issues)
3. **Submit new Issue**: Include error messages, configuration files, and reproduction steps
4. **Consult documentation**: [Complete documentation](README.md)

---

> 💡 **Tip**: Most issues are related to configuration file format, port conflicts, or permissions. It's recommended to check these common causes first. 