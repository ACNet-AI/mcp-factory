# FastMCP-Factory Demo

This directory contains demonstration of FastMCP-Factory usage.

## 📁 File Structure

```
examples/demo/
├── README.md          # This file
├── server.py          # Demo server
├── client.py          # Demo client
└── config.yaml        # Configuration
```

## 🚀 Quick Start

### Start Server
```bash
python examples/demo/server.py
```

### Run Client
```bash
# Basic mode
python examples/demo/client.py

# Management tools mode
python examples/demo/client.py --mgmt
```

## ⚙️ Configuration

Edit `config.yaml` to customize:
- Server port (default: 8888)
- Enable/disable management tools
- Log level

## 🔍 Troubleshooting

**Port occupied**: Change port in `config.yaml`
**Connection failed**: Ensure server is running

## 📚 Documentation

See [FastMCP-Factory Documentation](../../README.md) for more details. 