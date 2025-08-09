#!/usr/bin/env python3
"""
Official Qdrant MCP Server with Custom Embedding Provider
Uses the standard MCP server architecture with custom FastEmbed provider.
"""

import logging
import os

from mcp_server_qdrant.mcp_server import QdrantMCPServer
from mcp_server_qdrant.settings import EmbeddingProviderSettings, QdrantSettings, ToolSettings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_mcp_server() -> QdrantMCPServer:
    """Create and configure the MCP server with custom embedding provider."""
    
    # Create settings from environment variables
    tool_settings = ToolSettings()
    qdrant_settings = QdrantSettings()
    embedding_settings = EmbeddingProviderSettings()
    
    logger.info("Creating MCP server with settings:")
    logger.info(f"  Embedding Provider: {embedding_settings.provider_type}")
    logger.info(f"  Embedding Model: {embedding_settings.model_name}")
    logger.info(f"  Qdrant URL: {qdrant_settings.location}")
    logger.info(f"  Collection: {qdrant_settings.collection_name}")
    
    # Create MCP server with official architecture
    return QdrantMCPServer(
        tool_settings=tool_settings,
        qdrant_settings=qdrant_settings,
        embedding_provider_settings=embedding_settings,
        name="mcp-server-qdrant-custom",
        instructions="Qdrant MCP Server with Custom Embedding Provider for Social Media Content"
    )

def main():
    """Main entry point for the MCP server."""
    logger.info("Starting Qdrant MCP Server with Custom Embedding Provider")
    
    try:
        # Create server instance
        mcp_server = create_mcp_server()
        
        # Get server configuration from environment
        host = os.getenv("FASTMCP_HOST", "0.0.0.0")
        port = int(os.getenv("FASTMCP_PORT", "8080"))
        
        logger.info(f"Starting server on {host}:{port} with SSE transport...")
        
        # Start the server
        mcp_server.run(transport="sse", host=host, port=port)
        
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise

if __name__ == "__main__":
    main()
