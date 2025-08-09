import os
import logging
from simple_server import mcp

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    host = os.getenv("FASTMCP_HOST", "0.0.0.0")
    port = int(os.getenv("FASTMCP_PORT", "8080"))
    logger.info(f"Starting MCP server with SSE transport on {host}:{port}...")
    mcp.run(transport="sse", host=host, port=port)
