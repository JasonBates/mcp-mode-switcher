# MCP Mode Switcher

An MCP server that lets you switch between different MCP configuration profiles directly from inside Claude Desktop.

## Why?

Claude Desktop loads MCP servers at startup from `claude_desktop_config.json`. More MCPs = more tokens used on every message. This tool lets you:

- **Switch profiles** - Toggle between "full", "minimal", "research" modes etc.
- **Save snapshots** - Capture your current setup as a new profile
- **Auto-backup** - Every switch creates a timestamped backup

**Unlike CLI tools**, this runs as an MCP server - so you can switch modes by just asking Claude: *"Switch to minimal mode"*.

## Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mcp-mode-switcher.git ~/Projects/mcp-mode-switcher
   cd ~/Projects/mcp-mode-switcher
   ```

2. Create virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install mcp
   ```

3. Create the configs directory:
   ```bash
   mkdir -p ~/Library/Application\ Support/Claude/configs
   ```

4. Add to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "mcp-mode-switcher": {
         "command": "/path/to/mcp-mode-switcher/venv/bin/python",
         "args": ["/path/to/mcp-mode-switcher/server.py"]
       }
     }
   }
   ```

5. Restart Claude Desktop

## Tools

| Tool | Description |
|------|-------------|
| `list_modes()` | Show all available profiles with descriptions and token costs |
| `current_mode()` | Identify which profile is currently active |
| `switch_mode(mode, confirm)` | Switch to a different profile (requires confirmation) |
| `save_current_as_mode(name, description?, token_cost?)` | Save current config as a new profile |
| `list_backups()` | View timestamped backup history |

## Usage Examples

**In Claude Desktop:**

- "What modes are available?"
- "What mode am I in?"
- "Switch to minimal mode"
- "Save my current setup as 'writing' mode"
- "Show me my backups"

## File Structure

```
~/Library/Application Support/Claude/
├── claude_desktop_config.json      # Active config (Claude reads this)
├── configs/
│   ├── modes.json                  # Mode metadata (descriptions, token costs)
│   ├── full.json                   # Profile: all MCPs
│   ├── minimal.json                # Profile: minimal MCPs
│   └── [your-custom-modes].json    # Your saved profiles
└── backups/
    └── config.YYYY-MM-DD-HHMMSS.json  # Auto-backups before each switch
```

## Creating Profiles

### Option 1: Use the tool
Ask Claude: *"Save my current setup as 'research' mode with description 'For deep research work'"*

### Option 2: Manually
1. Create a config file in `~/Library/Application Support/Claude/configs/research.json`
2. Add metadata to `modes.json`:
   ```json
   {
     "research": {
       "description": "Research focused - perplexity, zotero, readwise",
       "token_cost": "~25k tokens"
     }
   }
   ```

## How It Works

1. Profiles are stored as complete `claude_desktop_config.json` files in `configs/`
2. Switching copies the selected profile to `claude_desktop_config.json`
3. Claude Desktop is automatically restarted to load the new config
4. A backup is created before every switch

## Requirements

- macOS (uses `osascript` and `open -a` for restart)
- Python 3.10+
- Claude Desktop

## License

MIT
