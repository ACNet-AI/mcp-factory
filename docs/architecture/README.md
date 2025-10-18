# MCP Factory Architecture Documentation

# # 📚 Documentation Navigation

MCP Factory adopts a layered modular architecture design.

**Current Status**: ⚠️ Functional but needs optimization

# ## 🌐 [Ecosystem Architecture](../../mcp-factory-platform/docs/architecture/ecosystem_architecture.md) ⭐

**Location**: `/Users/guyue/mcp-factory-platform/docs/architecture/ecosystem_architecture.md`

**Content**: Complete MCP Factory ecosystem architecture
- Four-layer architecture design (User → Agent → MCP Servers → Backend)
- All official MCP servers and their relationships
- Backend services architecture
- Typical usage scenarios and workflows

**Audience**: **Recommended for everyone** - Essential understanding of the entire ecosystem

# ## 🏗️ [Overall Architecture Design](./overall_architecture.md)

**Content**: Complete project architecture overview (mcp-factory framework internals)
- Current code scale analysis and issues
- Architecture problems and improvement suggestions
- Detailed refactoring roadmap

**Audience**: Newcomers, architects, technical leads

# ## ⚙️ [Configuration Management Architecture](./configuration_architecture.md)

**Content**: `config/` module design analysis
- Well-designed exemplary patterns
- Reference standard for other modules

**Audience**: Configuration-related developers, anyone learning good module design

# # 🎯 Core Design Principles

# ## 1. Single Responsibility ⚠️ **Partially Applied**
- ✅ **config/**: Excellent design, clear responsibilities
- ⚠️ **project/**: builder.py too large (1155 lines), needs splitting
- ⚠️ **factory/**: MCPFactory has too many functions (894 lines)
- ⚠️ **server/**: ManagedServer mixed responsibilities (940 lines)

# ## 2. Layered Collaboration 🟡 **Basically Applied**
```
User Interface Layer (CLI, MCP Server) ✅ Clear
     ↓
Core Coordination Layer (MCPFactory) ⚠️ Oversized, needs splitting
     ↓
Functional Module Layer (config ✅, project ⚠️, auth ✅, mounting ✅)
     ↓
Service Instance Layer (ManagedServer) ⚠️ Mixed responsibilities
```

# ## 3. Loose Coupling Design 🟡 **Needs Improvement**
- ✅ config module has good coupling
- ⚠️ Some modules interact directly, need coordination layer
- 🔧 **Improvement needed**: Introduce proper dependency injection

# # 🌟 Reference Standard: config/ Module

The config module demonstrates **excellent architecture**:

```python
# Reasonable scale, clear responsibilities
manager.py (457 lines)    # Configuration operations
schema.py (519 lines)     # Schema definitions  
__init__.py (24 lines)    # Public API

# Achieved effects:
✅ Easy to understand and maintain
✅ Simple unit testing
✅ Clear responsibilities
✅ Good documentation
```

**Please refer to this module when refactoring other components**

# # 📖 Contribution Guide

# ## Understanding Current State
1. **Start with** [Ecosystem Architecture](../../mcp-factory-platform/docs/architecture/ecosystem_architecture.md) to understand the big picture
2. Then read [Overall Architecture Design](./overall_architecture.md) for framework internals
3. Learn [Configuration Management Architecture](./configuration_architecture.md) good design
4. Understand problems and refactoring plans

# ## Design Decisions
1. **Apply single responsibility** - Each class one clear purpose
2. **Keep modules small** - Target 200-500 lines
3. **Use functional approaches** - Pure functions where possible
4. **Design for testing** - Make components easy to unit test

# # 🏁 Summary

MCP Factory has **solid architectural foundation**. The main work is **splitting oversized modules** into focused components, using the excellent `config/` module as reference.

**Key Point**: The architecture design itself is correct - we just need to implement it properly at the code level. 