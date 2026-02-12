"""
Utility functions for the Tuya MCP server.
"""

from typing import Any, Dict


def validate_device_id(device_id: str) -> tuple[bool, str]:
    """
    Validate the format of a Tuya device_id (22 alphanumeric characters).
    For device names, use TuyaClient.resolve_device_id().

    Args:
        device_id: Device ID to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not device_id:
        return False, "device_id cannot be empty"

    if not isinstance(device_id, str):
        return False, "device_id must be a string"

    if len(device_id) == 22 and device_id.isalnum():
        return True, ""

    return False, (
        f"'{device_id}' does not look like a valid device_id (22 alphanumeric chars). "
        "It might be a device name -- use TuyaClient.resolve_device_id()."
    )


def validate_brightness(brightness: int) -> tuple[bool, str]:
    """
    Validate a brightness value.

    Args:
        brightness: Brightness value (0-1000).

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not isinstance(brightness, int):
        return False, "Brightness must be an integer"

    if brightness < 0 or brightness > 1000:
        return False, f"Brightness must be between 0 and 1000. Got: {brightness}"

    return True, ""


def validate_color_temperature(temperature: int) -> tuple[bool, str]:
    """
    Validate a color temperature value.

    Args:
        temperature: Temperature value (0-1000).

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not isinstance(temperature, int):
        return False, "Temperature must be an integer"

    if temperature < 0 or temperature > 1000:
        return False, f"Temperature must be between 0 and 1000. Got: {temperature}"

    return True, ""


def validate_hsv(hue: int, saturation: int, value: int) -> tuple[bool, str]:
    """
    Validate HSV color values.

    Args:
        hue: Hue (0-360).
        saturation: Saturation (0-255).
        value: Value/Brightness (0-255).

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not isinstance(hue, int) or not isinstance(saturation, int) or not isinstance(value, int):
        return False, "HSV values must be integers"

    if not (0 <= hue <= 360):
        return False, f"hue must be between 0 and 360. Got: {hue}"

    if not (0 <= saturation <= 255):
        return False, f"saturation must be between 0 and 255. Got: {saturation}"

    if not (0 <= value <= 255):
        return False, f"value must be between 0 and 255. Got: {value}"

    return True, ""


def format_success_response(message: str, device_id: str = None, data: Any = None) -> Dict:
    """
    Format a success response.

    Args:
        message: Success message.
        device_id: Device ID (optional).
        data: Additional data (optional).

    Returns:
        Standardized response dict.
    """
    response = {
        "success": True,
        "message": message
    }

    if device_id:
        response["device_id"] = device_id

    if data is not None:
        response["data"] = data

    return response


def format_error_response(error: str, message: str, suggestion: str = None, device_id: str = None) -> Dict:
    """
    Format an error response.

    Args:
        error: Error type.
        message: Error message.
        suggestion: Suggestion to resolve the error (optional).
        device_id: Device ID (optional).

    Returns:
        Standardized response dict.
    """
    response = {
        "success": False,
        "error": error,
        "message": message
    }

    if suggestion:
        response["suggestion"] = suggestion

    if device_id:
        response["device_id"] = device_id

    return response


def hsv_to_tuya_format(hue: int, saturation: int, value: int) -> str:
    """
    Convert HSV values to Tuya's string format.

    Args:
        hue: Hue (0-360).
        saturation: Saturation (0-255).
        value: Value/Brightness (0-255).

    Returns:
        String in Tuya format (e.g., "01200500800").
    """
    # Tuya uses H:0-360, S:0-1000, V:0-1000
    tuya_s = int(saturation * 1000 / 255)
    tuya_v = int(value * 1000 / 255)

    return f"{hue:04d}{tuya_s:04d}{tuya_v:04d}"
