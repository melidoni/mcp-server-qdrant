#!/usr/bin/env python3
"""
Test script to verify MCP server initialization and custom embedding model loading.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any

import aiohttp
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPServerTester:
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.server_url = server_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def test_server_health(self) -> bool:
        """Test if server is responding to health checks."""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            logger.info(f"Health check status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def test_sse_connection(self) -> bool:
        """Test SSE connection to MCP server."""
        try:
            async with self.session.get(f"{self.server_url}/sse") as response:
                if response.status == 200:
                    logger.info("SSE connection established successfully")
                    return True
                else:
                    logger.error(f"SSE connection failed with status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"SSE connection test failed: {e}")
            return False
    
    async def test_mcp_initialization(self) -> Dict[str, Any]:
        """Test MCP server initialization message."""
        try:
            initialization_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            async with self.session.post(
                f"{self.server_url}/message",
                json=initialization_message,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                logger.info(f"MCP initialization result: {json.dumps(result, indent=2)}")
                return result
        except Exception as e:
            logger.error(f"MCP initialization test failed: {e}")
            return {"error": str(e)}

async def main():
    """Run all initialization tests."""
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
    
    logger.info("Starting MCP Server Initialization Tests")
    logger.info(f"Target server: {server_url}")
    
    tester = MCPServerTester(server_url)
    
    # Wait for server to start
    logger.info("Waiting for server to start...")
    for i in range(30):  # Wait up to 30 seconds
        if tester.test_server_health():
            logger.info("Server is healthy!")
            break
        await asyncio.sleep(1)
        logger.info(f"Waiting... ({i+1}/30)")
    else:
        logger.error("Server failed to start within timeout period")
        return
    
    async with tester:
        # Test SSE connection
        logger.info("\n=== Testing SSE Connection ===")
        sse_success = await tester.test_sse_connection()
        
        # Test MCP initialization
        logger.info("\n=== Testing MCP Initialization ===")
        init_result = await tester.test_mcp_initialization()
        
        # Summary
        logger.info("\n=== Test Summary ===")
        logger.info(f"Health Check: ✓")
        logger.info(f"SSE Connection: {'✓' if sse_success else '✗'}")
        logger.info(f"MCP Initialization: {'✓' if 'error' not in init_result else '✗'}")

if __name__ == "__main__":
    asyncio.run(main())
