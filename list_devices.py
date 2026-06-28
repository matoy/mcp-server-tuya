from src.mcp_server_tuya.config import load_config
from src.mcp_server_tuya.tuya_client import TuyaClient


def main() -> None:
    config = load_config()
    client = TuyaClient(config.access_id, config.access_key, config.api_endpoint)
    result = client.list_devices(use_cache=False)

    if not result.get("success"):
        print("Error:", result)
        return

    devices = result.get("data", [])
    for device in devices:
        print(
            f"{device.get('name', 'Unnamed'):<30} "
            f"{device.get('id', '')}  "
            f"online={device.get('online', False)}"
        )

    print(f"\n{len(devices)} device(s) found")


if __name__ == "__main__":
    main()
