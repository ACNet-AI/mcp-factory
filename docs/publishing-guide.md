# MCP Project Publishing Guide

This guide provides detailed instructions on how to publish your MCP project to GitHub and register it in the MCP Servers Hub.

# # 🎯 Publishing Overview

MCP Factory provides two publishing methods:
- **🚀 GitHub App Automatic Publishing** - Recommended approach, fully automated
- **📋 Manual Publishing** - Traditional approach, requires manual operations

# # 🚀 GitHub App Automatic Publishing (Recommended)

# ## Prerequisites

1. **Project Preparation**
   ```bash
   # Ensure project is built and contains Git repository
   mcpf project build my-project
   ```

2. **GitHub Account**
   - Valid GitHub account
   - Permission to install GitHub Apps

# ## Publishing Steps

# ### 1. Start Publishing Process

```bash
mcpf project publish my-project
```

# ### 2. GitHub App Installation

For first-time publishing, the system will prompt you to install the GitHub App:

```
🔗 Please complete GitHub App installation in your browser:
https://github.com/apps/mcp-project-manager/installations/new

✅ After installation is complete, the system will automatically continue the publishing process
```

# ### 3. Automated Process

After installation is complete, the system will automatically:
- ✅ Create GitHub repository
- ✅ Push code to repository
- ✅ Configure webhook
- ✅ Register to MCP Servers Hub

# ### 4. Publishing Complete

```
🎉 Publishing successful!
📦 Repository URL: https://github.com/your-username/my-project
🌐 MCP Hub: https://github.com/ACNet-AI/mcp-servers-hub
```

# # 🔧 Advanced Configuration

# ## Project Configuration

Configure publishing information in `pyproject.toml`:

```toml
[tool.mcp-servers-hub]
name = "my-awesome-server"
description = "An awesome MCP server"
author = "Your Name"
categories = ["tools", "api"]
license = "MIT"
github_username = "your-github-username"
installation_id = "12345678"  # Auto-filled
```

# ## Publishing Options

```bash
# Publish private repository
mcpf project publish my-project --private

# Specify GitHub username
mcpf project publish my-project --github-username your-username

# Force republish
mcpf project publish my-project --force
```

# # 📋 Manual Publishing Method

If GitHub App is not available, you can use manual publishing:

# ## 1. Prepare Git Repository

```bash
# Initialize Git repository (if not already initialized)
cd my-project
git init
git add .
git commit -m "Initial commit"
```

# ## 2. Create GitHub Repository

1. Visit [GitHub](https://github.com/new)
2. Create new repository
3. Add remote repository:
   ```bash
   git remote add origin https://github.com/your-username/my-project.git
   git push -u origin main
   ```

# ## 3. Manual Registration to Hub

1. Fork [MCP Servers Hub](https://github.com/ACNet-AI/mcp-servers-hub)
2. Edit `registry.json` file
3. Add your project information:
   ```json
   {
     "name": "my-project",
     "description": "My awesome MCP server",
     "repository": "https://github.com/your-username/my-project",
     "author": "Your Name",
     "categories": ["tools"]
   }
   ```
4. Create Pull Request

# # 🚨 Troubleshooting

# ## Common Issues

# ### 1. GitHub App Installation Failed

**Issue**: Cannot install GitHub App
**Solutions**:
- Ensure you have permission to install Apps
- Check network connection
- Try refreshing browser

# ### 2. Repository Creation Failed

**Issue**: "Repository already exists" error
**Solutions**:
```bash
# Use different project name
mcpf project publish my-project-v2

# Or delete existing repository and retry
```

# ### 3. Permission Issues

**Issue**: Code push failed
**Solutions**:
- Confirm GitHub App is properly installed
- Check repository permission settings
- Reinstall GitHub App

# ### 4. Network Connection Issues

**Issue**: Failed to connect to GitHub services
**Solutions**:
```bash
# Check network connectivity
curl -I https://api.github.com

# Use proxy if needed
export HTTPS_PROXY=http://your-proxy:port
mcpf project publish my-project
```

# ## Debug Mode

Enable verbose output for more information:

```bash
mcpf --verbose project publish my-project
```

# ## Reset Configuration

If you encounter persistent issues, reset configuration:

```bash
# Delete local configuration
rm -f .mcpf-config.json

# Reinitialize
mcpf project publish my-project
```

# # 📊 Publishing Status Check

# ## Check Publishing Status

```bash
# Check project status
mcpf project status my-project

# Check Hub registration status
curl -s "https://api.github.com/repos/ACNet-AI/mcp-servers-hub/contents/registry.json" | \
  jq '.content' | base64 -d | jq '.[] | select(.name == "my-project")'
```

# ## Verify Publishing Results

1. **GitHub Repository**: Visit repository URL to confirm code is pushed
2. **MCP Hub**: Check if it appears in [MCP Servers Hub](https://github.com/ACNet-AI/mcp-servers-hub)
3. **Webhook**: Verify webhook configuration is correct

# # 🔄 Update Published Project

# ## Push Updates

```bash
# Commit changes
git add .
git commit -m "Update features"

# Push to GitHub (webhook automatically triggers Hub update)
git push
```

# ## Manual Trigger Update

```bash
# Republish if needed
mcpf project publish my-project --force
```

# # 🔗 Related Resources

- [GitHub App Management](https://github.com/settings/installations)
- [MCP Servers Hub](https://github.com/ACNet-AI/mcp-servers-hub)
- [CLI Usage Guide](cli-guide.md)
- [Troubleshooting](troubleshooting.md)

---

> 💡 **Tip**: We recommend using GitHub App automatic publishing for the best user experience and minimal manual operations. 