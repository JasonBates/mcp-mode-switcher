#!/usr/bin/env python3
"""MCP Mode Switcher - Switch between different MCP configuration profiles."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("mcp-mode-switcher")

# Paths
CLAUDE_CONFIG_DIR = Path.home() / "Library" / "Application Support" / "Claude"
CLAUDE_CONFIG_FILE = CLAUDE_CONFIG_DIR / "claude_desktop_config.json"
CONFIGS_DIR = CLAUDE_CONFIG_DIR / "configs"
MODES_FILE = CONFIGS_DIR / "modes.json"
BACKUPS_DIR = CLAUDE_CONFIG_DIR / "backups"


def load_json_file(path: Path) -> dict | None:
    """Load a JSON file and return its contents."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_modes() -> dict:
    """Load modes from modes.json or auto-discover from config files.

    Returns a dict like:
    {
        "full": {"description": "...", "token_cost": "..."},
        "minimal": {"description": "...", "token_cost": "..."}
    }
    """
    # Try to load from modes.json first
    modes_data = load_json_file(MODES_FILE)
    if modes_data:
        return modes_data

    # Fallback: auto-discover from configs/*.json files
    modes = {}
    if CONFIGS_DIR.exists():
        for config_file in CONFIGS_DIR.glob("*.json"):
            if config_file.name == "modes.json":
                continue

            mode_name = config_file.stem
            config = load_json_file(config_file)
            if config and "mcpServers" in config:
                # Auto-generate description from MCP names
                mcps = [k for k in config["mcpServers"].keys() if k != "mcp-mode-switcher"]
                description = f"MCPs: {', '.join(mcps)}" if mcps else "No MCPs"
                modes[mode_name] = {
                    "description": description,
                    "token_cost": "unknown"
                }

    return modes


def get_mode_config_path(mode_name: str) -> Path:
    """Get the config file path for a mode."""
    return CONFIGS_DIR / f"{mode_name}.json"


def save_json_file(path: Path, data: dict) -> bool:
    """Save a dict to a JSON file. Returns True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def create_backup() -> str | None:
    """Create a timestamped backup of the current config.

    Returns the backup filename on success, None on failure.
    """
    current_config = load_json_file(CLAUDE_CONFIG_FILE)
    if current_config is None:
        return None

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup_file = BACKUPS_DIR / f"config.{timestamp}.json"

    if save_json_file(backup_file, current_config):
        return backup_file.name
    return None


def save_modes(modes: dict) -> bool:
    """Save modes metadata to modes.json."""
    return save_json_file(MODES_FILE, modes)


@mcp.tool()
def list_modes() -> str:
    """List all available MCP configuration profiles with descriptions and estimated token costs.

    Returns information about each available mode including:
    - Mode name
    - Description of included MCPs
    - Estimated token cost

    Note: mcp-mode-switcher (~2k tokens) is always included in every profile.
    """
    modes = get_modes()

    if not modes:
        return "No modes found. Config profiles should be in:\n" + str(CONFIGS_DIR)

    result = ["# Available MCP Modes\n"]
    result.append("(mcp-mode-switcher is included in all modes, adding ~2k tokens)\n")

    for mode_name, mode_info in modes.items():
        config_path = get_mode_config_path(mode_name)
        exists = config_path.exists()
        status = "✓" if exists else "✗ (config file missing)"

        result.append(f"\n## {mode_name} {status}")
        result.append(f"- **Description**: {mode_info.get('description', 'No description')}")
        result.append(f"- **Token cost**: {mode_info.get('token_cost', 'unknown')}")

        if exists:
            config = load_json_file(config_path)
            if config:
                servers = list(config.get("mcpServers", {}).keys())
                servers_str = ", ".join(servers)
                result.append(f"- **MCPs**: {servers_str}")

    return "\n".join(result)


@mcp.tool()
def current_mode() -> str:
    """Identify which MCP configuration profile is currently active.

    Reads the current claude_desktop_config.json and compares it against
    known profiles to determine which mode is active.

    Returns:
    - The name of the matching profile if found
    - "custom" if the current config doesn't match any profile
    - Error message if config cannot be read
    """
    current_config = load_json_file(CLAUDE_CONFIG_FILE)

    if current_config is None:
        return "Error: Could not read current Claude Desktop config"

    current_servers = set(current_config.get("mcpServers", {}).keys())

    result = ["# Current MCP Configuration\n"]
    result.append(f"**Active MCPs**: {', '.join(sorted(current_servers))}\n")

    # Check against each profile
    modes = get_modes()
    for mode_name, mode_info in modes.items():
        config_path = get_mode_config_path(mode_name)
        profile_config = load_json_file(config_path)

        if profile_config:
            profile_servers = set(profile_config.get("mcpServers", {}).keys())
            if current_servers == profile_servers:
                result.append(f"**Current mode**: `{mode_name}`")
                result.append(f"**Description**: {mode_info.get('description', 'No description')}")
                result.append(f"**Token cost**: {mode_info.get('token_cost', 'unknown')}")
                return "\n".join(result)

    # No match found
    result.append("**Current mode**: `custom` (does not match any predefined profile)")
    result.append("\nTo see available profiles, use `list_modes()`")

    return "\n".join(result)


@mcp.tool()
def switch_mode(mode: str, confirm: bool = False) -> str:
    """Switch to a different MCP configuration profile.

    Args:
        mode: The name of the profile to switch to
        confirm: Must be True to actually perform the switch. If False, returns a warning.

    WARNING: Switching modes will restart Claude Desktop and you will lose the current conversation!

    The switch process:
    1. Copies the selected profile to claude_desktop_config.json
    2. Quits Claude Desktop
    3. Waits 1 second
    4. Reopens Claude Desktop

    Returns:
    - Warning message if confirm=False
    - Success/error message if confirm=True
    """
    modes = get_modes()

    # Validate mode
    if mode not in modes:
        available = ", ".join(modes.keys()) if modes else "none"
        return f"Error: Unknown mode '{mode}'. Available modes: {available}"

    mode_info = modes[mode]
    config_path = get_mode_config_path(mode)

    # Check if config file exists
    if not config_path.exists():
        return f"Error: Config file not found: {config_path}"

    # If not confirmed, return warning
    if not confirm:
        return f"""⚠️ **WARNING: This action will restart Claude Desktop!**

You are about to switch to **{mode}** mode:
- {mode_info.get('description', 'No description')}
- Estimated token cost: {mode_info.get('token_cost', 'unknown')}

**This will:**
1. Replace your current claude_desktop_config.json
2. Quit Claude Desktop
3. Reopen Claude Desktop

**You will lose this conversation!**

To proceed, call `switch_mode(mode="{mode}", confirm=True)`"""

    # Confirmed - perform the switch
    try:
        # Create backup before switching
        backup_name = create_backup()

        # Read the new config
        new_config = load_json_file(config_path)
        if new_config is None:
            return f"Error: Could not read config file: {config_path}"

        # Write to main config file
        with open(CLAUDE_CONFIG_FILE, "w") as f:
            json.dump(new_config, f, indent=2)

        # Restart Claude Desktop
        restart_script = '''
        osascript -e 'quit app "Claude"'
        sleep 1
        open -a "Claude"
        '''

        subprocess.Popen(
            restart_script,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        backup_msg = f"Backup saved: `{backup_name}`" if backup_name else "Warning: Backup failed"

        return f"""✓ Switching to **{mode}** mode...

{backup_msg}
Config file updated. Claude Desktop is restarting.

(This message may not be visible as the app is restarting)"""

    except Exception as e:
        return f"Error: Failed to switch mode: {str(e)}"


@mcp.tool()
def save_current_as_mode(name: str, description: str = "", token_cost: str = "unknown") -> str:
    """Save the current Claude Desktop configuration as a new mode profile.

    Args:
        name: Name for the new mode (e.g., "writing", "coding", "research")
        description: Optional description of what this mode is for
        token_cost: Optional estimated token cost (e.g., "~20k tokens")

    This captures your current MCP setup as a reusable profile that you can
    switch back to later using switch_mode().

    Returns:
    - Success message with the new mode details
    - Error message if the save fails
    """
    # Validate name
    name = name.lower().strip().replace(" ", "-")
    if not name:
        return "Error: Mode name cannot be empty"

    if name == "modes":
        return "Error: 'modes' is a reserved name"

    # Check if mode already exists
    modes = get_modes()
    if name in modes:
        return f"Error: Mode '{name}' already exists. Choose a different name."

    # Read current config
    current_config = load_json_file(CLAUDE_CONFIG_FILE)
    if current_config is None:
        return "Error: Could not read current Claude Desktop config"

    # Generate description if not provided
    if not description:
        mcps = [k for k in current_config.get("mcpServers", {}).keys() if k != "mcp-mode-switcher"]
        description = f"MCPs: {', '.join(mcps)}" if mcps else "No MCPs configured"

    # Save the config file
    config_path = get_mode_config_path(name)
    if not save_json_file(config_path, current_config):
        return f"Error: Failed to save config file: {config_path}"

    # Update modes.json
    modes[name] = {
        "description": description,
        "token_cost": token_cost
    }
    if not save_modes(modes):
        return f"Warning: Config saved but failed to update modes.json"

    # Get MCP list for confirmation
    mcps = list(current_config.get("mcpServers", {}).keys())

    return f"""✓ Saved current config as **{name}** mode!

**Description**: {description}
**Token cost**: {token_cost}
**MCPs**: {', '.join(mcps)}
**Config file**: `{config_path.name}`

You can now switch to this mode anytime with `switch_mode("{name}")`"""


@mcp.tool()
def list_backups() -> str:
    """List all available configuration backups.

    Backups are created automatically before each mode switch.
    They can be used to restore a previous configuration if needed.
    """
    if not BACKUPS_DIR.exists():
        return "No backups found. Backups are created automatically when switching modes."

    backups = sorted(BACKUPS_DIR.glob("config.*.json"), reverse=True)

    if not backups:
        return "No backups found. Backups are created automatically when switching modes."

    result = ["# Configuration Backups\n"]
    result.append(f"Location: `{BACKUPS_DIR}`\n")

    for backup in backups[:10]:  # Show last 10
        result.append(f"- `{backup.name}`")

    if len(backups) > 10:
        result.append(f"\n... and {len(backups) - 10} more")

    result.append("\nTo restore a backup, copy it to `claude_desktop_config.json` and restart Claude.")

    return "\n".join(result)


if __name__ == "__main__":
    mcp.run()
