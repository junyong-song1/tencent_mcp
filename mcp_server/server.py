#!/usr/bin/env python3
"""Tencent Cloud MCP Server.

This is the main entry point for the MCP server that exposes
Tencent Cloud StreamLive and StreamLink resources to AI applications.

Usage:
    # Run as stdio server (for Claude Desktop, Cursor, etc.)
    python -m mcp_server.server
    
    # Or directly
    ./mcp_server/server.py
"""

import asyncio
import logging
import os
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mcp_server.resources import register_resources
from mcp_server.tools import register_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),  # MCP uses stderr for logging
    ],
)
logger = logging.getLogger(__name__)

# Global instances
_tencent_client = None
_schedule_manager = None


def get_tencent_client():
    """Get or create TencentCloudClient instance."""
    global _tencent_client
    if _tencent_client is None:
        from app.services.tencent_client import TencentCloudClient
        _tencent_client = TencentCloudClient()
        logger.info("TencentCloudClient initialized")
    return _tencent_client


def get_schedule_manager():
    """Get or create ScheduleManager instance."""
    global _schedule_manager
    if _schedule_manager is None:
        from app.services.schedule_manager import ScheduleManager
        _schedule_manager = ScheduleManager()
        logger.info("ScheduleManager initialized")
    return _schedule_manager


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("tencent-cloud-mcp")
    
    # Register resources
    register_resources(server, get_tencent_client, get_schedule_manager)
    logger.info("MCP Resources registered")
    
    # Register tools
    register_tools(server, get_tencent_client, get_schedule_manager)
    logger.info("MCP Tools registered")
    
    return server


async def main():
    """Main entry point for the MCP server."""
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = [
        "TENCENT_SECRET_ID",
        "TENCENT_SECRET_KEY",
        "TENCENT_REGION",
    ]
    
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        logger.error("Please set these in your .env file or environment")
        sys.exit(1)
    
    logger.info("Starting Tencent Cloud MCP Server...")
    logger.info(f"Region: {os.environ.get('TENCENT_REGION', 'ap-seoul')}")
    
    # Create server
    server = create_server()
    
    # Run with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP Server running on stdio")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
