"""Entry point for running mcp_server as a module.

Usage:
    python -m mcp_server
"""

from mcp_server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
