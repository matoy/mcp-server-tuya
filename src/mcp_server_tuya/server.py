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
# ROOM / LOCATION MANAGEMENT
# ============================================================================

@mcp.tool()
def tuya_list_rooms() -> str:
    """Get a list of all rooms/locations in your home with device counts"""
    result = tuya_client.list_rooms()
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_get_room_devices(room_id: str) -> str:
    """Get all devices in a specific room by room_id, including their status and names"""
    result = tuya_client.get_room_devices(room_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_add_device_to_room(device_id: str, room_id: str) -> str:
    """Add a device to a room by device_id or name (e.g. 'Living Room Light') and room_id"""
    result = tuya_client.add_device_to_room(device_id, room_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_remove_device_from_room(device_id: str, room_id: str) -> str:
    """Remove a device from a room by device_id or name (e.g. 'Living Room Light') and room_id"""
    result = tuya_client.remove_device_from_room(device_id, room_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_control_room_devices(room_id: str, commands: str) -> str:
    """Send commands to all devices in a room. commands must be a JSON string like: [{"code": "switch_1", "value": true}]"""
    try:
        commands_list = json.loads(commands)
        if not isinstance(commands_list, list):
            return json.dumps({
                "success": False,
                "error": "Invalid commands format",
                "message": 'commands must be a JSON array. Example: [{"code": "switch_1", "value": true}]'
            }, indent=2, ensure_ascii=False)

        result = tuya_client.control_room_devices(room_id, commands_list)
        return json.dumps(result, indent=2, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": "Invalid JSON in commands",
            "message": f'JSON parse error: {str(e)}. Example: [{{"code": "switch_1", "value": true}}]'
        }, indent=2, ensure_ascii=False)


# ============================================================================
# SCENES
# ============================================================================

@mcp.tool()
def tuya_list_scenes() -> str:
    """Get a list of all available scenes you can trigger in your home"""
    result = tuya_client.list_scenes()
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_trigger_scene(scene_id: str) -> str:
    """Trigger (execute) a scene by scene_id"""
    result = tuya_client.trigger_scene(scene_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# DEVICE SPECIFICATIONS & CAPABILITIES
# ============================================================================

@mcp.tool()
def tuya_get_device_specs(device_id: str) -> str:
    """Get detailed specifications for a Tuya device by device_id or name (e.g. 'Living Room Light'), including all available properties"""
    result = tuya_client.get_device_specs(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_get_device_capabilities(device_id: str) -> str:
    """Get all available commands/capabilities for a Tuya device by device_id or name (e.g. 'Living Room Light'), including property codes"""
    result = tuya_client.get_device_capabilities(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# THERMOSTAT & CLIMATE CONTROL
# ============================================================================

@mcp.tool()
def tuya_set_temperature(device_id: str, temperature: float) -> str:
    """Set target temperature for a thermostat device by device_id or name (e.g. 'Living Room Thermostat'). temperature is in degrees Celsius"""
    result = tuya_client.set_temperature(device_id, temperature)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_set_mode(device_id: str, mode: str) -> str:
    """Set operating mode for a thermostat by device_id or name (e.g. 'Living Room Thermostat'). Common modes: heat, cool, auto, wind, dry, off"""
    result = tuya_client.set_mode(device_id, mode)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# COUNTDOWN / TIMERS
# ============================================================================

@mcp.tool()
def tuya_set_countdown(device_id: str, seconds: int) -> str:
    """Set a countdown timer (auto-off after N seconds) for a device by device_id or name (e.g. 'Living Room Light')"""
    result = tuya_client.set_countdown(device_id, seconds)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_get_countdown(device_id: str) -> str:
    """Get the current countdown timer status for a device by device_id or name (e.g. 'Living Room Light')"""
    result = tuya_client.get_countdown(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# DEVICE HISTORY & EVENTS
# ============================================================================

@mcp.tool()
def tuya_get_device_events(device_id: str, limit: int = 20) -> str:
    """Get recent events/history for a device by device_id or name (e.g. 'Living Room Light'). Returns up to 'limit' recent events (default: 20)"""
    result = tuya_client.get_device_events(device_id, limit)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_get_energy_usage(device_id: str) -> str:
    """Get energy consumption data for a device by device_id or name (e.g. 'Smart Plug'). Only works with energy-capable devices"""
    result = tuya_client.get_energy_usage(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# DEVICE MANAGEMENT
# ============================================================================

@mcp.tool()
def tuya_rename_device(device_id: str, new_name: str) -> str:
    """Rename a device by device_id or name (e.g. 'Living Room Light'). new_name is the new custom name for the device"""
    result = tuya_client.rename_device(device_id, new_name)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_get_device_online_status(device_id: str) -> str:
    """Get detailed online status and connection information for a device by device_id or name (e.g. 'Living Room Light')"""
    result = tuya_client.get_device_online_status(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# BATCH COMMANDS
# ============================================================================

@mcp.tool()
def tuya_send_batch_commands(device_commands: str) -> str:
    """Send commands to multiple devices at once. device_commands must be a JSON string like: [{"device_id": "id1", "commands": [{"code": "switch_1", "value": true}]}, ...]"""
    try:
        commands_list = json.loads(device_commands)
        if not isinstance(commands_list, list):
            return json.dumps({
                "success": False,
                "error": "Invalid format",
                "message": 'device_commands must be a JSON array. Example: [{"device_id": "id1", "commands": [{"code": "switch_1", "value": true}]}]'
            }, indent=2, ensure_ascii=False)

        result = tuya_client.send_batch_commands(commands_list)
        return json.dumps(result, indent=2, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": "Invalid JSON",
            "message": f'JSON parse error: {str(e)}'
        }, indent=2, ensure_ascii=False)


# ============================================================================
# FAN CONTROL
# ============================================================================

@mcp.tool()
def tuya_set_fan_speed(device_id: str, speed: int) -> str:
    """Set fan speed for a fan device by device_id or name (e.g. 'Living Room Fan'). speed is typically 0-100 or device-specific"""
    result = tuya_client.set_fan_speed(device_id, speed)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_set_fan_mode(device_id: str, mode: str) -> str:
    """Set fan operating mode by device_id or name (e.g. 'Living Room Fan'). Common modes: manual, auto, sleep, natural"""
    result = tuya_client.set_fan_mode(device_id, mode)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# BLINDS / CURTAINS / COVERS
# ============================================================================

@mcp.tool()
def tuya_open_blind(device_id: str) -> str:
    """Open a blind/curtain/cover completely by device_id or name (e.g. 'Living Room Blinds')"""
    result = tuya_client.open_blind(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_close_blind(device_id: str) -> str:
    """Close a blind/curtain/cover completely by device_id or name (e.g. 'Living Room Blinds')"""
    result = tuya_client.close_blind(device_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def tuya_set_blind_position(device_id: str, position: int) -> str:
    """Set blind/curtain/cover position by device_id or name (e.g. 'Living Room Blinds'). position: 0=closed, 100=open, or any value in between"""
    result = tuya_client.set_blind_position(device_id, position)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# MCP RESOURCES
# ============================================================================

@mcp.resource("tuya://devices/list")
def get_devices_list() -> str:
    """List of all available Tuya devices"""
    result = tuya_client.list_devices()
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.resource("tuya://rooms/list")
def get_rooms_list() -> str:
    """List of all rooms/locations in your home"""
    result = tuya_client.list_rooms()
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.resource("tuya://scenes/list")
def get_scenes_list() -> str:
    """List of all available scenes"""
    result = tuya_client.list_scenes()
    return json.dumps(result, indent=2, ensure_ascii=False)
