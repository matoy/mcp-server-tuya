# mcp-server-tuya

[![PyPI version](https://badge.fury.io/py/mcp-server-tuya.svg)](https://pypi.org/project/mcp-server-tuya/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that lets AI assistants (**Claude, ChatGPT, Copilot, Cursor**, and more) control your **Tuya / Smart Life** smart home devices.

<p align="center">
  <img src="https://img.shields.io/badge/MCP-Compatible-green?style=for-the-badge" alt="MCP Compatible" />
  <img src="https://img.shields.io/badge/Tuya-Smart%20Home-orange?style=for-the-badge" alt="Tuya Smart Home" />
</p>

## Features

- **33 tools** for comprehensive smart home control:
  - 🏠 **Room Management**: List rooms, manage devices per room, bulk room control
  - 🎬 **Scenes**: List and trigger automated scenes
  - 💡 **Lighting**: On/off, brightness, color temperature, RGB color control
  - 🌡️ **Climate**: Thermostat control, operating modes, temperature setting
  - ⏱️ **Timers**: Countdown timers for auto-off functionality
  - 🔌 **Power**: Smart plug controls with energy monitoring
  - 🎚️ **Fans**: Speed and mode control for fan devices
  - 🪟 **Blinds**: Open/close/position control for curtains and blinds
  - 📊 **Analytics**: Device events history, energy consumption data
  - ⚙️ **Device Mgmt**: Rename devices, check online status, device capabilities
  - 🔋 **Batch Operations**: Send commands to multiple devices at once
- **Device name resolution** — use friendly names like "Living Room Light" instead of IDs
- **Intelligent caching** — configurable TTL to reduce API calls
- **All Tuya regions** — EU, US, CN, IN
- **Zero config files** — credentials via environment variables
- **Works with** Claude Desktop, ChatGPT, GitHub Copilot, Cursor, Windsurf, Cline, and any MCP-compatible client

## Quick Start

### 1. Get Tuya Credentials

1. Go to [Tuya IoT Platform](https://iot.tuya.com/) and create an account
2. Create a **Cloud Project** (select your region and "Smart Home" industry)
3. Go to **Devices** > **Link Tuya App Account** and link your Smart Life / Tuya Smart app
4. Copy your **Access ID** and **Access Secret** from the project overview

### 2. Configure your MCP client

<details>
<summary><b>Claude Desktop</b></summary>

Add this to your config file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tuya": {
      "command": "uvx",
      "args": ["mcp-server-tuya"],
      "env": {
        "TUYA_ACCESS_ID": "your_access_id",
        "TUYA_ACCESS_KEY": "your_access_key",
        "TUYA_API_ENDPOINT": "https://openapi.tuyaeu.com"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add tuya -- uvx mcp-server-tuya
```

Then set your environment variables:
```bash
export TUYA_ACCESS_ID="your_access_id"
export TUYA_ACCESS_KEY="your_access_key"
export TUYA_API_ENDPOINT="https://openapi.tuyaeu.com"
```
</details>

<details>
<summary><b>Cursor</b></summary>

Add this to `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "tuya": {
      "command": "uvx",
      "args": ["mcp-server-tuya"],
      "env": {
        "TUYA_ACCESS_ID": "your_access_id",
        "TUYA_ACCESS_KEY": "your_access_key",
        "TUYA_API_ENDPOINT": "https://openapi.tuyaeu.com"
      }
    }
  }
}
```
</details>

<details>
<summary><b>VS Code (GitHub Copilot)</b></summary>

Add this to your `.vscode/settings.json`:

```json
{
  "mcp": {
    "servers": {
      "tuya": {
        "command": "uvx",
        "args": ["mcp-server-tuya"],
        "env": {
          "TUYA_ACCESS_ID": "your_access_id",
          "TUYA_ACCESS_KEY": "your_access_key",
          "TUYA_API_ENDPOINT": "https://openapi.tuyaeu.com"
        }
      }
    }
  }
}
```
</details>

<details>
<summary><b>ChatGPT / Other MCP clients</b></summary>

Any MCP-compatible client can use this server. The general pattern is:
- **Command**: `uvx`
- **Args**: `["mcp-server-tuya"]`
- **Environment variables**: `TUYA_ACCESS_ID`, `TUYA_ACCESS_KEY`, `TUYA_API_ENDPOINT`

Refer to your client's documentation for how to configure MCP servers.
</details>

### 3. Restart your client

That's it! Ask your AI assistant things like:
- *"List all my devices"*
- *"Turn off the living room light"*
- *"Set the bedroom light to 50% brightness"*
- *"What's the temperature in the kitchen?"*
- *"Turn everything off"*

## Installation

### With uvx (recommended)

No installation needed — `uvx` runs it directly:

```bash
uvx mcp-server-tuya
```

### With pip

```bash
pip install mcp-server-tuya
```

### From GitHub

```bash
pip install git+https://github.com/juanmartinsantos/mcp-server-tuya.git
```

## Available Tools

All tools accept either a **device ID** or a **device name** (e.g., `"Living Room Light"`).

### 📱 Discovery & Status
| Tool | Description |
|------|-------------|
| `tuya_list_devices` | List all devices with IDs, names, categories, and online status |
| `tuya_get_device_status` | Get current device state (power, brightness, temperature, etc.) |
| `tuya_get_device_info` | Get detailed device info (model, firmware, capabilities) |

### 🏠 Room / Location Management
| Tool | Description |
|------|-------------|
| `tuya_list_rooms` | List all rooms in your home |
| `tuya_get_room_devices` | Get all devices in a specific room |
| `tuya_add_device_to_room` | Add a device to a room |
| `tuya_remove_device_from_room` | Remove a device from a room |
| `tuya_control_room_devices` | Send commands to all devices in a room at once |

### 💡 Basic Control
| Tool | Description |
|------|-------------|
| `tuya_turn_on_device` | Turn on a device (supports multi-switch devices) |
| `tuya_turn_off_device` | Turn off a device (supports multi-switch devices) |
| `tuya_toggle_device` | Toggle device on/off |

### 🎨 Lighting Control
| Tool | Description |
|------|-------------|
| `tuya_set_brightness` | Set light brightness (0-1000) |
| `tuya_set_color_temperature` | Set color temperature: warm (0) to cool (1000) |
| `tuya_set_color` | Set RGB color using HSV: hue (0-360), saturation (0-255), value (0-255) |

### 🎬 Scenes
| Tool | Description |
|------|-------------|
| `tuya_list_scenes` | List all available scenes |
| `tuya_trigger_scene` | Trigger (execute) a scene by ID |

### 🌡️ Climate Control
| Tool | Description |
|------|-------------|
| `tuya_set_temperature` | Set target temperature for thermostat |
| `tuya_set_mode` | Set operating mode (heat, cool, auto, wind, dry, off) |

### ⏱️ Timers
| Tool | Description |
|------|-------------|
| `tuya_set_countdown` | Set countdown timer (auto-off after N seconds) |
| `tuya_get_countdown` | Get active countdown timer status |

### 📊 Device Specifications & Monitoring
| Tool | Description |
|------|-------------|
| `tuya_get_device_specs` | Get device specifications and available properties |
| `tuya_get_device_capabilities` | Get all available commands/properties for a device |
| `tuya_get_device_events` | Get recent events/history for a device |
| `tuya_get_energy_usage` | Get energy consumption data (for smart plugs) |
| `tuya_get_device_online_status` | Get detailed online status and connection info |

### ⚙️ Device Management
| Tool | Description |
|------|-------------|
| `tuya_rename_device` | Rename a device |
| `tuya_send_command` | Send any custom command to a device |
| `tuya_send_batch_commands` | Send commands to multiple devices at once |

### 🎚️ Fan Control
| Tool | Description |
|------|-------------|
| `tuya_set_fan_speed` | Set fan speed (0-100 or device-specific) |
| `tuya_set_fan_mode` | Set fan operating mode (manual, auto, sleep, natural) |

### 🪟 Blinds / Curtains / Covers
| Tool | Description |
|------|-------------|
| `tuya_open_blind` | Open a blind/curtain/cover completely |
| `tuya_close_blind` | Close a blind/curtain/cover completely |
| `tuya_set_blind_position` | Set blind position (0=closed, 100=open) |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TUYA_ACCESS_ID` | Yes | — | Tuya Cloud API Access ID |
| `TUYA_ACCESS_KEY` | Yes | — | Tuya Cloud API Access Secret |
| `TUYA_API_ENDPOINT` | No | `https://openapi.tuyaeu.com` | API endpoint (see regions below) |
| `TUYA_CACHE_TTL` | No | `60` | Device list cache duration (seconds) |
| `TUYA_REQUEST_TIMEOUT` | No | `10` | API request timeout (seconds) |

### API Endpoints by Region

| Region | Endpoint |
|--------|----------|
| Europe | `https://openapi.tuyaeu.com` |
| Americas | `https://openapi.tuyaus.com` |
| China | `https://openapi.tuyacn.com` |
| India | `https://openapi.tuyain.com` |

## Local Development

```bash
# Clone the repository
git clone https://github.com/juanmartinsantos/mcp-server-tuya.git
cd mcp-server-tuya

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install in editable mode
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the server
mcp-server-tuya
# or: python -m mcp_server_tuya
```

## Testing

### Unit Tests

Install dev dependencies, then run pytest:

```bash
# with uv
uv sync --dev
uv run pytest -q

# or with pip
pip install -e ".[dev]"
pytest -q
```

### API Smoke Test (Real Tuya Cloud)

Run a non-destructive smoke test against your configured Tuya account:

```bash
uv run python smoke_test.py
```

Useful options:

```bash
# target a specific device id or exact name
uv run python smoke_test.py --device "your_device_id_or_name"

# include write checks (temporary rename + restore)
uv run python smoke_test.py --include-write
```

The smoke test validates device listing, core read APIs, and optional endpoints (events/energy/rooms/scenes).
Only required check failures make the command return a non-zero exit code.

## Troubleshooting

### "TUYA_ACCESS_ID environment variable is required"
Your credentials are not set. Make sure you've added the `env` section to your MCP client config.

### "API error: permission deny"
Your Tuya Cloud project doesn't have the right permissions. Go to Tuya IoT Platform > your project > **Service API** and enable **IoT Core** and **Smart Home** APIs.

### "Device not found"
The device name doesn't match. Use `tuya_list_devices` first to see the exact names of your devices.

### Server won't start
Make sure you have `uv` installed. Install it with:
```bash
# Windows
winget install --id=astral-sh.uv

# macOS
brew install uv
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- [FastMCP](https://github.com/jlowin/fastmcp) — Pythonic MCP server framework
- [tuya-connector-python](https://github.com/tuya/tuya-connector-python) — Official Tuya Cloud SDK
- [Model Context Protocol](https://modelcontextprotocol.io/) — by Anthropic
