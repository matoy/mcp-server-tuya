"""
Tuya API client with caching and error handling.

Wrapper around tuya-connector-python that provides:
- Device list caching with configurable TTL
- Robust error handling with helpful messages
- Standardized response format
- Device name resolution (use names instead of IDs)
"""

import sys
import time
from typing import Dict, List, Optional, Any
from tuya_connector import TuyaOpenAPI


class TuyaClient:
    """Wrapper client for the Tuya Cloud API."""

    def __init__(self, access_id: str, access_key: str, endpoint: str, cache_ttl: int = 60):
        """
        Initialize the Tuya client.

        Args:
            access_id: Tuya Cloud access ID.
            access_key: Tuya Cloud access key.
            endpoint: API endpoint URL.
            cache_ttl: Cache time-to-live in seconds (default: 60).
        """
        self.access_id = access_id
        self.access_key = access_key
        self.endpoint = endpoint
        self.cache_ttl = cache_ttl

        # Initialize Tuya API
        self.openapi = TuyaOpenAPI(endpoint, access_id, access_key)
        self.openapi.connect()

        # Device cache
        self._device_cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[float] = None

        sys.stderr.write(f"Tuya client initialized: {endpoint}\n")

    def _is_cache_valid(self) -> bool:
        """Check if the device cache is still valid."""
        if self._device_cache is None or self._cache_timestamp is None:
            return False

        elapsed = time.time() - self._cache_timestamp
        return elapsed < self.cache_ttl

    def _invalidate_cache(self):
        """Invalidate the device cache."""
        self._device_cache = None
        self._cache_timestamp = None
        sys.stderr.write("Device cache invalidated\n")

    def resolve_device_id(self, device_identifier: str) -> Dict[str, Any]:
        """
        Resolve a device identifier (ID or name) to a device_id.

        Args:
            device_identifier: A device_id (22 chars) or device name.

        Returns:
            Dict with "success", "device_id", and optionally "error"/"message".
        """
        if not device_identifier or not device_identifier.strip():
            return {
                "success": False,
                "error": "Empty device identifier",
                "message": "You must provide a device_id or device name"
            }

        device_identifier = device_identifier.strip()

        # If it has 22 alphanumeric chars, treat it as a direct device_id
        if len(device_identifier) == 22 and device_identifier.isalnum():
            return {"success": True, "device_id": device_identifier}

        # It's a name -> search in cache
        if not self._is_cache_valid():
            list_result = self.list_devices(use_cache=False)
            if not list_result.get("success"):
                return {
                    "success": False,
                    "error": "Could not fetch device list to resolve name",
                    "message": list_result.get("message", "Unknown error")
                }

        search_lower = device_identifier.lower()
        matches = []
        for device in (self._device_cache or []):
            device_name = device.get("name", "").lower()
            if search_lower == device_name:
                return {"success": True, "device_id": device["id"], "matched_name": device["name"]}
            if search_lower in device_name or device_name in search_lower:
                matches.append(device)

        if len(matches) == 1:
            return {"success": True, "device_id": matches[0]["id"], "matched_name": matches[0]["name"]}
        elif len(matches) > 1:
            names_list = [f"  - {m['name']} (ID: {m['id']})" for m in matches]
            return {
                "success": False,
                "error": "Multiple devices match",
                "message": f"Found {len(matches)} devices matching '{device_identifier}':\n" + "\n".join(names_list),
                "suggestion": "Specify the exact name or use the device_id"
            }
        else:
            available = [f"  - {d['name']} (ID: {d['id']})" for d in (self._device_cache or [])]
            return {
                "success": False,
                "error": "Device not found",
                "message": f"No device found with name '{device_identifier}'",
                "suggestion": "Available devices:\n" + "\n".join(available) if available else "No devices in cache. Use tuya_list_devices first."
            }

    def list_devices(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        List all Tuya devices.

        Uses the /v2.0/cloud/thing/device endpoint that lists devices
        linked via the Smart Life / Tuya Smart app.

        Args:
            use_cache: If True, use cached data if available.

        Returns:
            Standardized response dict with device list.
        """
        # Use cache if available and valid
        if use_cache and self._is_cache_valid():
            sys.stderr.write("Using device cache\n")
            return {
                "success": True,
                "message": "Device list retrieved from cache",
                "data": self._device_cache
            }

        try:
            all_devices_raw = []
            page_no = 1
            page_size = 20
            max_pages = 20

            while max_pages > 0:
                max_pages -= 1
                response = self.openapi.get(
                    "/v2.0/cloud/thing/device",
                    {"page_no": page_no, "page_size": page_size}
                )

                if not response.get("success"):
                    # Code 1110 = rate limit, retry with backoff
                    if response.get("code") == 1110:
                        wait_time = 2 ** min(page_no, 4)
                        sys.stderr.write(f"Rate limited, retrying in {wait_time}s...\n")
                        time.sleep(wait_time)
                        continue
                    sys.stderr.write(f"Error listing devices: {response}\n")
                    return {
                        "success": False,
                        "error": "Could not retrieve device list",
                        "message": f"API error: {response.get('msg', 'Unknown error')}",
                        "suggestion": "Check your Tuya Cloud API credentials"
                    }

                devices = response.get("result", [])
                all_devices_raw.extend(devices)

                # If fewer than page_size returned, no more pages
                if len(devices) < page_size:
                    break
                page_no += 1

            all_devices = []
            for device in all_devices_raw:
                # customName is the user-assigned name in the app
                # name is the generic product name
                custom_name = device.get("customName", "").strip()
                product_name_raw = device.get("name", "")
                display_name = custom_name if custom_name else product_name_raw or "Unnamed"

                all_devices.append({
                    "id": device.get("id", ""),
                    "name": display_name,
                    "category": device.get("category", "unknown"),
                    "product_name": device.get("productName", ""),
                    "online": device.get("isOnline", False),
                    "ip": device.get("ip", "")
                })

            # Update cache
            self._device_cache = all_devices
            self._cache_timestamp = time.time()

            sys.stderr.write(f"Found {len(all_devices)} devices\n")

            return {
                "success": True,
                "message": f"Found {len(all_devices)} devices",
                "data": all_devices
            }

        except Exception as e:
            sys.stderr.write(f"Exception listing devices: {str(e)}\n")
            self._invalidate_cache()
            return {
                "success": False,
                "error": "Exception connecting to Tuya API",
                "message": str(e),
                "suggestion": "Check your internet connection and credentials"
            }

    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Get the current status of a device.

        Args:
            device_id: Device ID or name.

        Returns:
            Standardized response dict with device status.
        """
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]

        try:
            response = self.openapi.get(f"/v1.0/iot-03/devices/{device_id}/status")

            if not response.get("success"):
                sys.stderr.write(f"Error getting status: {response}\n")
                return {
                    "success": False,
                    "error": "Could not get device status",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id,
                    "suggestion": "Check that the device_id is correct. Use tuya_list_devices to see available devices."
                }

            # Convert data points to a more readable format
            status_data = {}
            for item in response.get("result", []):
                status_data[item["code"]] = item["value"]

            return {
                "success": True,
                "message": "Device status retrieved successfully",
                "device_id": device_id,
                "data": status_data
            }

        except Exception as e:
            sys.stderr.write(f"Exception getting status: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception getting device status",
                "message": str(e),
                "device_id": device_id
            }

    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a device.

        Args:
            device_id: Device ID or name.

        Returns:
            Standardized response dict with device info.
        """
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]

        try:
            response = self.openapi.get(f"/v1.0/iot-03/devices/{device_id}")

            if not response.get("success"):
                return {
                    "success": False,
                    "error": "Could not get device information",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id,
                    "suggestion": "Check that the device_id is correct"
                }

            device_info = response.get("result", {})

            return {
                "success": True,
                "message": "Device information retrieved successfully",
                "device_id": device_id,
                "data": {
                    "id": device_info.get("id", ""),
                    "name": device_info.get("name", ""),
                    "category": device_info.get("category", ""),
                    "product_name": device_info.get("product_name", ""),
                    "model": device_info.get("model", ""),
                    "online": device_info.get("online", False),
                    "ip": device_info.get("ip", ""),
                    "sub": device_info.get("sub", False)
                }
            }

        except Exception as e:
            sys.stderr.write(f"Exception getting info: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception getting device information",
                "message": str(e),
                "device_id": device_id
            }

    def send_command(self, device_id: str, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send commands to a device.

        Args:
            device_id: Device ID or name.
            commands: List of commands, e.g. [{"code": "switch_1", "value": True}].

        Returns:
            Standardized response dict.
        """
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]

        try:
            response = self.openapi.post(
                f"/v1.0/iot-03/devices/{device_id}/commands",
                {"commands": commands}
            )

            if not response.get("success"):
                sys.stderr.write(f"Error sending command: {response}\n")
                return {
                    "success": False,
                    "error": "Could not send command",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id,
                    "commands": commands,
                    "suggestion": "Check that the device is online and the command is valid"
                }

            return {
                "success": True,
                "message": "Command sent successfully",
                "device_id": device_id,
                "commands": commands,
                "data": response.get("result", {})
            }

        except Exception as e:
            sys.stderr.write(f"Exception sending command: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception sending command",
                "message": str(e),
                "device_id": device_id,
                "commands": commands
            }
