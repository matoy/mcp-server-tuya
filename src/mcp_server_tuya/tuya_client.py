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
            page_size = 20  # Tuya API limit per page
            last_row_key = ""  # Cursor for pagination (empty = first page)
            seen_device_ids = set()  # Track seen devices to prevent duplicates
            page_num = 0

            while True:
                page_num += 1
                params = {"page_size": page_size}
                if last_row_key:
                    params["last_row_key"] = last_row_key

                response = self.openapi.get(
                    "/v2.0/cloud/thing/device",
                    params
                )

                if not response.get("success"):
                    # Code 1110 = rate limit, retry with backoff
                    if response.get("code") == 1110:
                        wait_time = 2 ** min(page_num, 4)
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

                result = response.get("result", {})

                # The v2 API returns result as a dict with nested devices list
                # and cursor-based pagination via last_row_key
                if isinstance(result, dict):
                    devices = result.get("devices", [])
                    has_more = result.get("has_more", False)
                    last_row_key = result.get("last_row_key", "")
                else:
                    # Fallback: some API versions return result as a direct list
                    devices = result if isinstance(result, list) else []
                    has_more = len(devices) >= page_size
                    last_row_key = ""

                new_devices_count = 0
                for device in devices:
                    device_id = device.get("id", "")
                    if device_id and device_id not in seen_device_ids:
                        all_devices_raw.append(device)
                        seen_device_ids.add(device_id)
                        new_devices_count += 1

                sys.stderr.write(f"Page {page_num}: got {len(devices)} devices, {new_devices_count} new, has_more={has_more}\n")

                if not has_more or not last_row_key:
                    sys.stderr.write("Pagination complete\n")
                    break

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

    # ========================================================================
    # ROOM / LOCATION MANAGEMENT
    # ========================================================================

    def list_rooms(self) -> Dict[str, Any]:
        """List all rooms/locations in the home."""
        try:
            response = self.openapi.get("/v2.0/cloud/thing/space")
            
            if not response.get("success"):
                sys.stderr.write(f"Error listing rooms: {response}\n")
                return {
                    "success": False,
                    "error": "Could not retrieve room list",
                    "message": f"API error: {response.get('msg', 'Unknown error')}"
                }
            
            rooms = []
            for room in response.get("result", []):
                rooms.append({
                    "id": room.get("spaceId", ""),
                    "name": room.get("name", "Unnamed"),
                    "device_count": room.get("deviceCount", 0)
                })
            
            return {
                "success": True,
                "message": f"Found {len(rooms)} rooms",
                "data": rooms
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception listing rooms: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception listing rooms",
                "message": str(e)
            }

    def get_room_devices(self, room_id: str) -> Dict[str, Any]:
        """Get all devices in a specific room."""
        try:
            response = self.openapi.get(
                f"/v2.0/cloud/thing/space/{room_id}/devices"
            )
            
            if not response.get("success"):
                sys.stderr.write(f"Error getting room devices: {response}\n")
                return {
                    "success": False,
                    "error": "Could not retrieve room devices",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "room_id": room_id
                }
            
            devices = []
            for device in response.get("result", []):
                devices.append({
                    "id": device.get("id", ""),
                    "name": device.get("customName", "") or device.get("name", "Unnamed"),
                    "category": device.get("category", "unknown"),
                    "online": device.get("isOnline", False)
                })
            
            return {
                "success": True,
                "message": f"Found {len(devices)} devices in room",
                "room_id": room_id,
                "data": devices
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception getting room devices: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception getting room devices",
                "message": str(e),
                "room_id": room_id
            }

    def add_device_to_room(self, device_id: str, room_id: str) -> Dict[str, Any]:
        """Add a device to a room."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            response = self.openapi.post(
                f"/v2.0/cloud/thing/space/{room_id}/devices",
                {"deviceId": device_id}
            )
            
            if not response.get("success"):
                sys.stderr.write(f"Error adding device to room: {response}\n")
                return {
                    "success": False,
                    "error": "Could not add device to room",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id,
                    "room_id": room_id
                }
            
            return {
                "success": True,
                "message": "Device added to room successfully",
                "device_id": device_id,
                "room_id": room_id
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception adding device to room: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception adding device to room",
                "message": str(e),
                "device_id": device_id,
                "room_id": room_id
            }

    def remove_device_from_room(self, device_id: str, room_id: str) -> Dict[str, Any]:
        """Remove a device from a room."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            response = self.openapi.delete(
                f"/v2.0/cloud/thing/space/{room_id}/devices/{device_id}"
            )
            
            if not response.get("success"):
                sys.stderr.write(f"Error removing device from room: {response}\n")
                return {
                    "success": False,
                    "error": "Could not remove device from room",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id,
                    "room_id": room_id
                }
            
            return {
                "success": True,
                "message": "Device removed from room successfully",
                "device_id": device_id,
                "room_id": room_id
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception removing device from room: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception removing device from room",
                "message": str(e),
                "device_id": device_id,
                "room_id": room_id
            }

    def control_room_devices(self, room_id: str, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send commands to all devices in a room."""
        try:
            response = self.openapi.post(
                f"/v2.0/cloud/thing/space/{room_id}/devices/commands",
                {"commands": commands}
            )
            
            if not response.get("success"):
                sys.stderr.write(f"Error controlling room devices: {response}\n")
                return {
                    "success": False,
                    "error": "Could not control room devices",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "room_id": room_id
                }
            
            return {
                "success": True,
                "message": "Commands sent to room devices successfully",
                "room_id": room_id,
                "data": response.get("result", {})
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception controlling room devices: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception controlling room devices",
                "message": str(e),
                "room_id": room_id
            }

    # ========================================================================
    # SCENES
    # ========================================================================

    def list_scenes(self) -> Dict[str, Any]:
        """List all available scenes."""
        try:
            response = self.openapi.get("/v2.0/cloud/scene")
            
            if not response.get("success"):
                sys.stderr.write(f"Error listing scenes: {response}\n")
                return {
                    "success": False,
                    "error": "Could not retrieve scene list",
                    "message": f"API error: {response.get('msg', 'Unknown error')}"
                }
            
            scenes = []
            for scene in response.get("result", []):
                scenes.append({
                    "id": scene.get("sceneId", ""),
                    "name": scene.get("sceneName", "Unnamed"),
                    "description": scene.get("description", "")
                })
            
            return {
                "success": True,
                "message": f"Found {len(scenes)} scenes",
                "data": scenes
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception listing scenes: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception listing scenes",
                "message": str(e)
            }

    def trigger_scene(self, scene_id: str) -> Dict[str, Any]:
        """Trigger (execute) a scene."""
        try:
            response = self.openapi.post(
                f"/v2.0/cloud/scene/{scene_id}/trigger"
            )
            
            if not response.get("success"):
                sys.stderr.write(f"Error triggering scene: {response}\n")
                return {
                    "success": False,
                    "error": "Could not trigger scene",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "scene_id": scene_id
                }
            
            return {
                "success": True,
                "message": "Scene triggered successfully",
                "scene_id": scene_id
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception triggering scene: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception triggering scene",
                "message": str(e),
                "scene_id": scene_id
            }

    # ========================================================================
    # DEVICE SPECIFICATIONS & CAPABILITIES
    # ========================================================================

    def get_device_specs(self, device_id: str) -> Dict[str, Any]:
        """Get device specifications and available properties."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            response = self.openapi.get(f"/v1.0/iot-03/devices/{device_id}/specification")
            
            if not response.get("success"):
                sys.stderr.write(f"Error getting device specs: {response}\n")
                return {
                    "success": False,
                    "error": "Could not retrieve device specifications",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id
                }
            
            return {
                "success": True,
                "message": "Device specifications retrieved successfully",
                "device_id": device_id,
                "data": response.get("result", {})
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception getting device specs: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception getting device specifications",
                "message": str(e),
                "device_id": device_id
            }

    def get_device_capabilities(self, device_id: str) -> Dict[str, Any]:
        """Get device capabilities (available commands/properties)."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            response = self.openapi.get(f"/v1.0/iot-03/devices/{device_id}/functions")
            
            if not response.get("success"):
                sys.stderr.write(f"Error getting device capabilities: {response}\n")
                return {
                    "success": False,
                    "error": "Could not retrieve device capabilities",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id
                }
            
            capabilities = []
            for cap in response.get("result", []):
                capabilities.append({
                    "code": cap.get("code", ""),
                    "name": cap.get("name", ""),
                    "description": cap.get("desc", "")
                })
            
            return {
                "success": True,
                "message": "Device capabilities retrieved successfully",
                "device_id": device_id,
                "data": capabilities
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception getting device capabilities: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception getting device capabilities",
                "message": str(e),
                "device_id": device_id
            }

    # ========================================================================
    # THERMOSTAT & CLIMATE CONTROL
    # ========================================================================

    def set_temperature(self, device_id: str, temperature: float) -> Dict[str, Any]:
        """Set target temperature for a thermostat device."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            # Tuya stores temperature as integer (usually in 0.5°C increments)
            temp_value = int(temperature * 2) / 2
            
            result = self.send_command(
                device_id,
                [{"code": "temp_set", "value": temp_value}]
            )
            return result
        
        except Exception as e:
            sys.stderr.write(f"Exception setting temperature: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception setting temperature",
                "message": str(e),
                "device_id": device_id
            }

    def set_mode(self, device_id: str, mode: str) -> Dict[str, Any]:
        """Set operating mode (heat/cool/auto/off) for a thermostat."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        # Common mode codes: heat, cool, auto, wind, dry, off
        try:
            result = self.send_command(
                device_id,
                [{"code": "mode", "value": mode}]
            )
            return result
        
        except Exception as e:
            sys.stderr.write(f"Exception setting mode: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception setting mode",
                "message": str(e),
                "device_id": device_id
            }

    # ========================================================================
    # COUNTDOWN / TIMERS
    # ========================================================================

    def set_countdown(self, device_id: str, seconds: int) -> Dict[str, Any]:
        """Set a countdown timer (auto-off after N seconds)."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            result = self.send_command(
                device_id,
                [{"code": "countdown_1", "value": seconds}]
            )
            return result
        
        except Exception as e:
            sys.stderr.write(f"Exception setting countdown: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception setting countdown",
                "message": str(e),
                "device_id": device_id
            }

    def get_countdown(self, device_id: str) -> Dict[str, Any]:
        """Get active countdown timer status."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        status_result = self.get_device_status(device_id)
        if not status_result.get("success"):
            return status_result
        
        countdown_value = status_result.get("data", {}).get("countdown_1", 0)
        return {
            "success": True,
            "message": "Countdown retrieved successfully",
            "device_id": device_id,
            "countdown_seconds": countdown_value
        }

    # ========================================================================
    # DEVICE HISTORY & EVENTS
    # ========================================================================

    def get_device_events(self, device_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get recent events/history for a device."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            response = self.openapi.get(
                f"/v1.0/iot-03/devices/{device_id}/logs",
                {"limit": limit}
            )
            
            if not response.get("success"):
                sys.stderr.write(f"Error getting device events: {response}\n")
                return {
                    "success": False,
                    "error": "Could not retrieve device events",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id
                }
            
            return {
                "success": True,
                "message": f"Retrieved {len(response.get('result', []))} events",
                "device_id": device_id,
                "data": response.get("result", [])
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception getting device events: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception getting device events",
                "message": str(e),
                "device_id": device_id
            }

    def get_energy_usage(self, device_id: str) -> Dict[str, Any]:
        """Get energy consumption data for a device."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            response = self.openapi.get(f"/v1.0/iot-03/devices/{device_id}/energy")
            
            if not response.get("success"):
                sys.stderr.write(f"Error getting energy usage: {response}\n")
                return {
                    "success": False,
                    "error": "Could not retrieve energy usage",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id
                }
            
            return {
                "success": True,
                "message": "Energy usage retrieved successfully",
                "device_id": device_id,
                "data": response.get("result", {})
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception getting energy usage: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception getting energy usage",
                "message": str(e),
                "device_id": device_id
            }

    # ========================================================================
    # DEVICE MANAGEMENT
    # ========================================================================

    def rename_device(self, device_id: str, new_name: str) -> Dict[str, Any]:
        """Rename a device."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            response = self.openapi.post(
                f"/v1.0/iot-03/devices/{device_id}",
                {"name": new_name}
            )
            
            if not response.get("success"):
                sys.stderr.write(f"Error renaming device: {response}\n")
                return {
                    "success": False,
                    "error": "Could not rename device",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id,
                    "new_name": new_name
                }
            
            return {
                "success": True,
                "message": "Device renamed successfully",
                "device_id": device_id,
                "new_name": new_name
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception renaming device: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception renaming device",
                "message": str(e),
                "device_id": device_id,
                "new_name": new_name
            }

    def get_device_online_status(self, device_id: str) -> Dict[str, Any]:
        """Get detailed online status of a device."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            response = self.openapi.get(f"/v1.0/iot-03/devices/{device_id}")
            
            if not response.get("success"):
                sys.stderr.write(f"Error getting online status: {response}\n")
                return {
                    "success": False,
                    "error": "Could not get device status",
                    "message": f"API error: {response.get('msg', 'Unknown error')}",
                    "device_id": device_id
                }
            
            device_info = response.get("result", {})
            return {
                "success": True,
                "message": "Device status retrieved successfully",
                "device_id": device_id,
                "data": {
                    "online": device_info.get("online", False),
                    "ip": device_info.get("ip", ""),
                    "last_seen": device_info.get("lastSeen", "")
                }
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception getting online status: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception getting online status",
                "message": str(e),
                "device_id": device_id
            }

    # ========================================================================
    # BATCH COMMANDS
    # ========================================================================

    def send_batch_commands(self, device_commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send multiple commands to different devices."""
        try:
            results = []
            for item in device_commands:
                device_id = item.get("device_id", "")
                commands = item.get("commands", [])
                
                result = self.send_command(device_id, commands)
                results.append({
                    "device_id": device_id,
                    "success": result.get("success"),
                    "message": result.get("message")
                })
            
            success_count = sum(1 for r in results if r.get("success"))
            return {
                "success": True,
                "message": f"Sent commands to {len(device_commands)} devices, {success_count} successful",
                "data": results
            }
        
        except Exception as e:
            sys.stderr.write(f"Exception sending batch commands: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception sending batch commands",
                "message": str(e)
            }

    # ========================================================================
    # FAN CONTROL
    # ========================================================================

    def set_fan_speed(self, device_id: str, speed: int) -> Dict[str, Any]:
        """Set fan speed (0-100 or device-specific scale)."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            result = self.send_command(
                device_id,
                [{"code": "fan_speed", "value": speed}]
            )
            return result
        
        except Exception as e:
            sys.stderr.write(f"Exception setting fan speed: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception setting fan speed",
                "message": str(e),
                "device_id": device_id
            }

    def set_fan_mode(self, device_id: str, mode: str) -> Dict[str, Any]:
        """Set fan mode (manual/auto/sleep, etc.)."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            result = self.send_command(
                device_id,
                [{"code": "fan_mode", "value": mode}]
            )
            return result
        
        except Exception as e:
            sys.stderr.write(f"Exception setting fan mode: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception setting fan mode",
                "message": str(e),
                "device_id": device_id
            }

    # ========================================================================
    # BLINDS / CURTAINS / COVERS
    # ========================================================================

    def open_blind(self, device_id: str) -> Dict[str, Any]:
        """Open a blind/curtain/cover."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            result = self.send_command(
                device_id,
                [{"code": "control", "value": "open"}]
            )
            return result
        
        except Exception as e:
            sys.stderr.write(f"Exception opening blind: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception opening blind",
                "message": str(e),
                "device_id": device_id
            }

    def close_blind(self, device_id: str) -> Dict[str, Any]:
        """Close a blind/curtain/cover."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        try:
            result = self.send_command(
                device_id,
                [{"code": "control", "value": "close"}]
            )
            return result
        
        except Exception as e:
            sys.stderr.write(f"Exception closing blind: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception closing blind",
                "message": str(e),
                "device_id": device_id
            }

    def set_blind_position(self, device_id: str, position: int) -> Dict[str, Any]:
        """Set blind position (0=closed, 100=open)."""
        resolved = self.resolve_device_id(device_id)
        if not resolved.get("success"):
            return resolved
        device_id = resolved["device_id"]
        
        if not (0 <= position <= 100):
            return {
                "success": False,
                "error": "Invalid position",
                "message": f"Position must be between 0 and 100. Got: {position}",
                "device_id": device_id
            }
        
        try:
            result = self.send_command(
                device_id,
                [{"code": "percent_control", "value": position}]
            )
            return result
        
        except Exception as e:
            sys.stderr.write(f"Exception setting blind position: {str(e)}\n")
            return {
                "success": False,
                "error": "Exception setting blind position",
                "message": str(e),
                "device_id": device_id
            }
