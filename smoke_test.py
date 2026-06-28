import argparse
import sys
from typing import Any, Callable, Dict, Tuple

from src.mcp_server_tuya.config import load_config
from src.mcp_server_tuya.tuya_client import TuyaClient


CheckFn = Callable[[], Dict[str, Any]]


def _is_optional_unavailable(result: Dict[str, Any]) -> bool:
    """Detect optional checks that are unavailable in current Tuya project permissions/features."""
    api_code = str(result.get("api_code", ""))
    message = str(result.get("message", "")).lower()
    error = str(result.get("error", "")).lower()
    combined = f"{message} {error}"

    if api_code in {"40001900", "1108", "1106"}:
        return True

    known_markers = [
        "no space permission",
        "uri path invalid",
        "permission deny",
        "illegal permission",
        "not support",
    ]
    return any(marker in combined for marker in known_markers)


def run_check(name: str, fn: CheckFn, required: bool = True) -> Tuple[bool, Dict[str, Any]]:
    try:
        result = fn()
    except Exception as exc:
        print(f"[FAIL] {name}: exception={exc}")
        return False, {"success": False, "message": str(exc)}

    ok = bool(result.get("success"))
    is_skip = (not ok) and (not required) and _is_optional_unavailable(result)
    status = "PASS" if ok else ("SKIP" if is_skip else "FAIL")
    suffix = "" if required else " (optional)"
    message = result.get("message", "")
    print(f"[{status}] {name}{suffix}: {message}")

    if not ok and not is_skip:
        error = result.get("error", "")
        suggestion = result.get("suggestion", "")
        if error:
            print(f"       error: {error}")
        if suggestion:
            print(f"       hint : {suggestion}")

    return ok or is_skip, result


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for Tuya client APIs")
    parser.add_argument("--device", help="Device id or exact name to target for device-level checks")
    parser.add_argument(
        "--include-write",
        action="store_true",
        help="Also run write checks (rename + restore original name)",
    )
    args = parser.parse_args()

    config = load_config()
    client = TuyaClient(config.access_id, config.access_key, config.api_endpoint)

    required_failures = 0

    ok_devices, devices_res = run_check("list_devices", lambda: client.list_devices(use_cache=False), required=True)
    if not ok_devices:
        return 1

    devices = devices_res.get("data", [])
    print(f"       devices found: {len(devices)}")

    target_identifier = args.device
    if not target_identifier:
        if not devices:
            print("[FAIL] device-level checks: no devices available")
            required_failures += 1
            target_identifier = None
        else:
            target_identifier = devices[0].get("id")
            print(f"       using target device: {target_identifier}")

    if target_identifier:
        checks = [
            ("get_device_status", lambda: client.get_device_status(target_identifier), True),
            ("get_device_info", lambda: client.get_device_info(target_identifier), True),
            ("get_device_specs", lambda: client.get_device_specs(target_identifier), True),
            ("get_device_capabilities", lambda: client.get_device_capabilities(target_identifier), True),
            ("get_device_online_status", lambda: client.get_device_online_status(target_identifier), True),
            ("get_device_events", lambda: client.get_device_events(target_identifier, limit=20), False),
            ("get_energy_usage", lambda: client.get_energy_usage(target_identifier), False),
        ]

        for name, fn, required in checks:
            ok, _ = run_check(name, fn, required=required)
            if required and not ok:
                required_failures += 1

        if args.include_write:
            info = client.get_device_info(target_identifier)
            original_name = ""
            if info.get("success"):
                original_name = info.get("data", {}).get("name", "")

            if original_name:
                tmp_name = f"{original_name}-smoke"
                ok_rename, _ = run_check(
                    "rename_device(temp)",
                    lambda: client.rename_device(target_identifier, tmp_name),
                    required=False,
                )
                if ok_rename:
                    run_check(
                        "rename_device(restore)",
                        lambda: client.rename_device(target_identifier, original_name),
                        required=False,
                    )
            else:
                print("[FAIL] rename_device(temp) (optional): could not resolve current name")

    room_checks = [
        ("list_rooms", lambda: client.list_rooms()),
        ("list_scenes", lambda: client.list_scenes()),
    ]
    for name, fn in room_checks:
        run_check(name, fn, required=False)

    if required_failures:
        print(f"\nSmoke test finished with {required_failures} required failure(s).")
        return 1

    print("\nSmoke test passed for required checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
