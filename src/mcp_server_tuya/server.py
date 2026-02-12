"""
MCP server for Tuya Smart Home devices.

This server provides tools for Claude and other LLMs to interact
with Tuya devices using the Model Context Protocol.
"""

import sys
import json
from fastmcp import FastMCP

from .config import load_config
from .tuya_client import TuyaClient


# Initialize configuration and Tuya client
try:
    config = load_config()
    tuya_client = TuyaClient(
        access_id=config.access_id,
        access_key=config.access_key,
        endpoint=config.api_endpoint,
        cache_ttl=config.cache_ttl
    )
    sys.stderr.write(f"Tuya MCP server initialized: {config}\n")
except Exception as e:
    sys.stderr.write(f"ERROR initializing server: {str(e)}\n")
    raise


# Create FastMCP server
mcp = FastMCP("tuya-smart-home")


# ============================================================================
# DISCOVERY & STATUS TOOLS
# ============================================================================

@mcp.tool()
def tuya_list_devices() -> str:
    """Get a list of all available Tuya devices with their IDs, names, categories, and online status"""
    result = tuya_client.list_devices()
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_get_device_status(device_id: str) -> str:
    """Get the current status of a specific Tuya device by device_id or name (e.g. 'Living Room Light'), including power state, brightness, color, temperature and other properties"""
    result = tuya_client.get_device_status(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_get_device_info(device_id: str) -> str:
    """Get detailed information about a specific Tuya device by device_id or name (e.g. 'Living Room Light'), including capabilities, category, model and firmware version"""
    result = tuya_client.get_device_info(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# BASIC CONTROL TOOLS
# ============================================================================

@mcp.tool()
def tuya_turn_on_device(device_id: str, switch_code: str = "switch_1") -> str:
    """Turn on a Tuya device by device_id or name (e.g. 'Living Room Light'). For devices with multiple switches, specify switch_code (switch_1, switch_2, etc.)"""
    result = tuya_client.send_command(
        device_id,
        [{"code": switch_code, "value": True}]
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_turn_off_device(device_id: str, switch_code: str = "switch_1") -> str:
    """Turn off a Tuya device by device_id or name (e.g. 'Living Room Light'). For devices with multiple switches, specify switch_code (switch_1, switch_2, etc.)"""
    result = tuya_client.send_command(
        device_id,
        [{"code": switch_code, "value": False}]
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_toggle_device(device_id: str, switch_code: str = "switch_1") -> str:
    """Toggle a Tuya device on/off by device_id or name (e.g. 'Living Room Light'). Turns it on if off, turns it off if on"""
    # Resolve name to ID once
    resolved = tuya_client.resolve_device_id(device_id)
    if not resolved.get("success"):
        return json.dumps(resolved, indent=2, ensure_ascii=False)
    actual_id = resolved["device_id"]

    # Get current state
    status = tuya_client.get_device_status(actual_id)
    if not status.get("success"):
        return json.dumps(status, indent=2, ensure_ascii=False)

    # Get switch state
    current_state = status.get("data", {}).get(switch_code, False)
    new_state = not current_state

    # Send toggle command
    result = tuya_client.send_command(
        actual_id,
        [{"code": switch_code, "value": new_state}]
    )

    if result.get("success"):
        result["message"] = f"Device toggled: {'on' if new_state else 'off'}"

    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# ADVANCED CONTROL TOOLS
# ============================================================================

@mcp.tool()
def tuya_set_brightness(device_id: str, brightness: int) -> str:
    """Set the brightness of a Tuya light by device_id or name (e.g. 'Living Room Light'). brightness must be between 0 (minimum) and 1000 (maximum)"""
    # Validate range
    if brightness < 0 or brightness > 1000:
        return json.dumps({
            "success": False,
            "error": "Invalid brightness value",
            "message": f"Brightness must be between 0 and 1000. Got: {brightness}"
        }, indent=2, ensure_ascii=False)

    result = tuya_client.send_command(
        device_id,
        [{"code": "bright_value", "value": brightness}]
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_set_color_temperature(device_id: str, temperature: int) -> str:
    """Set the color temperature of a Tuya light by device_id or name (e.g. 'Living Room Light'). temperature must be between 0 (warm white) and 1000 (cool white)"""
    # Validate range
    if temperature < 0 or temperature > 1000:
        return json.dumps({
            "success": False,
            "error": "Invalid temperature value",
            "message": f"Temperature must be between 0 and 1000. Got: {temperature}"
        }, indent=2, ensure_ascii=False)

    result = tuya_client.send_command(
        device_id,
        [{"code": "temp_value", "value": temperature}]
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_set_color(device_id: str, hue: int, saturation: int, value: int) -> str:
    """Set the color of a Tuya RGB light by device_id or name (e.g. 'Living Room Light') using HSV values. hue: 0-360, saturation: 0-255, value: 0-255"""
    # Validate ranges
    if not (0 <= hue <= 360):
        return json.dumps({
            "success": False,
            "error": "Invalid hue value",
            "message": f"hue must be between 0 and 360. Got: {hue}"
        }, indent=2, ensure_ascii=False)

    if not (0 <= saturation <= 255):
        return json.dumps({
            "success": False,
            "error": "Invalid saturation value",
            "message": f"saturation must be between 0 and 255. Got: {saturation}"
        }, indent=2, ensure_ascii=False)

    if not (0 <= value <= 255):
        return json.dumps({
            "success": False,
            "error": "Invalid value",
            "message": f"value must be between 0 and 255. Got: {value}"
        }, indent=2, ensure_ascii=False)

    # Convert HSV to Tuya format (H:0-360, S:0-1000, V:0-1000)
    hsv_string = f"{hue:04d}{int(saturation*1000/255):04d}{int(value*1000/255):04d}"

    result = tuya_client.send_command(
        device_id,
        [{"code": "colour_data", "value": hsv_string}]
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_send_command(device_id: str, commands: str) -> str:
    """Send custom commands to a Tuya device by device_id or name (e.g. 'Living Room Light'). commands must be a JSON string like: [{"code": "switch_1", "value": true}]"""
    try:
        commands_list = json.loads(commands)
        if not isinstance(commands_list, list):
            return json.dumps({
                "success": False,
                "error": "Invalid commands format",
                "message": 'commands must be a JSON array. Example: [{"code": "switch_1", "value": true}]'
            }, indent=2, ensure_ascii=False)

        result = tuya_client.send_command(device_id, commands_list)
        return json.dumps(result, indent=2, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": "Invalid JSON in commands",
            "message": f'JSON parse error: {str(e)}. Example: [{{"code": "switch_1", "value": true}}]'
        }, indent=2, ensure_ascii=False)


# ============================================================================
# MCP RESOURCES
# ============================================================================

@mcp.resource("tuya://devices/list")
def get_devices_list() -> str:
    """List of all available Tuya devices"""
    result = tuya_client.list_devices()
    return json.dumps(result, indent=2, ensure_ascii=False)
