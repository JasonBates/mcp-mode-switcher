# MCP Mode Switcher

## Overview
A FastMCP server that manages Claude Desktop MCP configuration profiles, allowing quick switching between different sets of MCP servers.

## Architecture

```
mcp-mode-switcher/
├── server.py          # Single-file FastMCP server (main implementation)
└── pyproject.toml     # Dependencies managed by uv
```

This is a single-file server - all logic is in `server.py`.

## Key Components

### Configuration Paths
- Base directory: `~/Library/Application Support/Claude/`
- Active config: `claude_desktop_config.json` (read by Claude Desktop)
- Profiles directory: `configs/` (stores mode definitions)
- Backups directory: `backups/` (timestamped auto-backups)
- Metadata file: `modes.json` (mode descriptions and token costs)

### MCP Tools (5 tools)
- `list_modes()` - Display available profiles with descriptions
- `current_mode()` - Identify which profile is currently active
- `switch_mode(mode, confirm=False)` - Switch profiles (requires confirmation)
- `save_current_as_mode(name, description, token_cost)` - Save current config as new profile
- `list_backups()` - Show backup history

### System Integration
- Uses macOS `osascript` to quit Claude Desktop app
- Uses `open -a 'Claude'` to relaunch after config switch
- Creates timestamped backup before every mode switch

## Secrets Management
- No secrets required - this server only manages local config files

## Running
```bash
uv run mcp-mode-switcher
```

## Important Notes
- Switching modes will **terminate the current Claude conversation**
- The server creates automatic backups before each switch
- Confirmation is required for destructive operations

## Dependencies
- `fastmcp>=2.0.0` - MCP framework
