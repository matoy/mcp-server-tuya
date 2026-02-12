"""
Configuration module for the Tuya MCP server.

Loads configuration from environment variables. Supports .env files
for local development via python-dotenv.
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Tuya MCP server configuration."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Tuya Cloud API credentials
        self.access_id = os.getenv("TUYA_ACCESS_ID")
        self.access_key = os.getenv("TUYA_ACCESS_KEY")
        self.api_endpoint = os.getenv("TUYA_API_ENDPOINT", "https://openapi.tuyaeu.com")

        # Server settings
        self.cache_ttl = int(os.getenv("TUYA_CACHE_TTL", "60"))
        self.request_timeout = int(os.getenv("TUYA_REQUEST_TIMEOUT", "10"))

        # Validate required credentials
        self._validate()

    def _validate(self):
        """Validate that all required credentials are present."""
        if not self.access_id:
            sys.stderr.write(
                "ERROR: TUYA_ACCESS_ID is not set.\n"
                "Set it as an environment variable or in the Claude Desktop config.\n"
            )
            raise ValueError("TUYA_ACCESS_ID environment variable is required")

        if not self.access_key:
            sys.stderr.write(
                "ERROR: TUYA_ACCESS_KEY is not set.\n"
                "Set it as an environment variable or in the Claude Desktop config.\n"
            )
            raise ValueError("TUYA_ACCESS_KEY environment variable is required")

    def __repr__(self):
        """String representation (without exposing credentials)."""
        return (
            f"Config(endpoint={self.api_endpoint}, "
            f"cache_ttl={self.cache_ttl}s, "
            f"timeout={self.request_timeout}s)"
        )


def load_config() -> Config:
    """
    Load and return server configuration.

    Returns:
        Config: Configuration object with loaded credentials.

    Raises:
        ValueError: If required credentials are missing.
    """
    return Config()
