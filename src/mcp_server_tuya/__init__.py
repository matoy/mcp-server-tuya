"""
MCP server for Tuya smart home devices.

Control your Tuya/Smart Life devices through Claude Desktop
and other MCP-compatible clients.
"""

__version__ = "0.1.1"


def main():
    """Entry point for the mcp-server-tuya command."""
    from .server import mcp
    mcp.run()
