#!/usr/bin/env python3
"""
Test script to verify custom embedding model registration and functionality.
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Any

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingModelTester:
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.server_url = server_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_embedding_query(self, query: str) -> Dict[str, Any]:
        """Test embedding generation for a query."""
        try:
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "find",
                    "arguments": {
                        "query": query,
                        "limit": 5
                    }
                }
            }
            
            async with self.session.post(
                f"{self.server_url}/message",
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                logger.info(f"Query '{query}' result: {json.dumps(result, indent=2)}")
                return result
        except Exception as e:
            logger.error(f"Embedding query test failed: {e}")
            return {"error": str(e)}
    
    async def test_store_operation(self, information: str, metadata: Dict[str, str]) -> Dict[str, Any]:
        """Test storing information with embedding."""
        try:
            message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "store",
                    "arguments": {
                        "information": information,
                        "metadata": json.dumps(metadata)
                    }
                }
            }
            
            async with self.session.post(
                f"{self.server_url}/message",
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                logger.info(f"Store operation result: {json.dumps(result, indent=2)}")
                return result
        except Exception as e:
            logger.error(f"Store operation test failed: {e}")
            return {"error": str(e)}

    async def test_tools_list(self) -> Dict[str, Any]:
        """Test retrieving available tools."""
        try:
            message = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/list",
                "params": {}
            }
            
            async with self.session.post(
                f"{self.server_url}/message",
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                logger.info(f"Available tools: {json.dumps(result, indent=2)}")
                return result
        except Exception as e:
            logger.error(f"Tools list test failed: {e}")
            return {"error": str(e)}

async def main():
    """Run embedding model tests."""
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
    
    logger.info("Starting Embedding Model Tests")
    logger.info(f"Target server: {server_url}")
    
    test_queries = [
        "Find posts about sustainable fashion",
        "Show me content about mental health awareness",
        "Search for posts about travel photography",
    ]
    
    test_store_data = {
        "information": "A social media post about eco-friendly lifestyle tips",
        "metadata": {
            "caption": "🌱 5 simple ways to live more sustainably: 1) Use reusable bags 2) Reduce plastic consumption 3) Support local businesses 4) Choose renewable energy 5) Practice mindful consumption #sustainability #ecolife",
            "platform": "instagram",
            "category": "lifestyle"
        }
    }
    
    async with EmbeddingModelTester(server_url) as tester:
        # Test tools list first
        logger.info("\n=== Testing Tools List ===")
        tools_result = await tester.test_tools_list()
        
        # Test store operation first
        logger.info("\n=== Testing Store Operation ===")
        store_result = await tester.test_store_operation(
            test_store_data["information"], 
            test_store_data["metadata"]
        )
        
        # Test embedding queries
        logger.info("\n=== Testing Embedding Queries ===")
        query_results = []
        for query in test_queries:
            logger.info(f"\nTesting query: '{query}'")
            result = await tester.test_embedding_query(query)
            query_results.append(result)
            await asyncio.sleep(1)  # Small delay between queries
        
        # Summary
        logger.info("\n=== Test Summary ===")
        logger.info(f"Tools List: {'✓' if 'error' not in tools_result else '✗'}")
        logger.info(f"Store Operation: {'✓' if 'error' not in store_result else '✗'}")
        
        successful_queries = sum(1 for result in query_results if 'error' not in result)
        logger.info(f"Query Operations: {successful_queries}/{len(query_results)} successful")
        
        if successful_queries > 0:
            logger.info("✓ Custom embedding model appears to be working correctly!")
        else:
            logger.error("✗ Issues detected with embedding model functionality")

if __name__ == "__main__":
    asyncio.run(main())
