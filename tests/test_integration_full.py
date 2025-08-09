#!/usr/bin/env python3
"""
Comprehensive integration test for MCP Server with custom embedding model.
Tests the complete workflow: initialization -> model loading -> Qdrant operations -> query processing.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, List

import aiohttp
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPIntegrationTester:
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.server_url = server_url
        self.session = None
        self.test_results = {}
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def wait_for_server(self, timeout: int = 120) -> bool:
        """Wait for server to be ready with extended timeout for model loading."""
        logger.info(f"Waiting for server to start (timeout: {timeout}s)...")
        
        for i in range(timeout):
            try:
                response = requests.get(f"{self.server_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info(f"✓ Server is healthy after {i+1} seconds!")
                    return True
            except:
                pass
            
            if i % 10 == 0:  # Log every 10 seconds
                logger.info(f"Still waiting... ({i+1}/{timeout}s)")
            time.sleep(1)
        
        logger.error(f"✗ Server failed to start within {timeout} seconds")
        return False
    
    async def test_mcp_initialize(self) -> bool:
        """Test MCP protocol initialization."""
        logger.info("Testing MCP initialization...")
        
        try:
            init_message = {
                "jsonrpc": "2.0",
                "id": "init-1",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {
                            "listChanged": True
                        },
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name": "integration-test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            async with self.session.post(
                f"{self.server_url}/message",
                json=init_message,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("✓ MCP initialization successful")
                    self.test_results['mcp_init'] = True
                    return True
                else:
                    logger.error(f"✗ MCP initialization failed: HTTP {response.status}")
                    self.test_results['mcp_init'] = False
                    return False
                    
        except Exception as e:
            logger.error(f"✗ MCP initialization error: {e}")
            self.test_results['mcp_init'] = False
            return False
    
    async def test_tools_available(self) -> bool:
        """Test that required tools are available."""
        logger.info("Testing tool availability...")
        
        try:
            tools_message = {
                "jsonrpc": "2.0",
                "id": "tools-1",
                "method": "tools/list",
                "params": {}
            }
            
            async with self.session.post(
                f"{self.server_url}/message",
                json=tools_message,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    tools = result.get("result", {}).get("tools", [])
                    tool_names = [tool.get("name") for tool in tools]
                    
                    required_tools = ["find", "store"]
                    available_tools = [name for name in required_tools if name in tool_names]
                    
                    if len(available_tools) == len(required_tools):
                        logger.info(f"✓ All required tools available: {available_tools}")
                        self.test_results['tools_available'] = True
                        return True
                    else:
                        missing = set(required_tools) - set(available_tools)
                        logger.error(f"✗ Missing tools: {missing}")
                        self.test_results['tools_available'] = False
                        return False
                else:
                    logger.error(f"✗ Tools list failed: HTTP {response.status}")
                    self.test_results['tools_available'] = False
                    return False
                    
        except Exception as e:
            logger.error(f"✗ Tools availability error: {e}")
            self.test_results['tools_available'] = False
            return False
    
    async def test_store_functionality(self) -> bool:
        """Test store operation with custom embedding model."""
        logger.info("Testing store functionality...")
        
        test_data = [
            {
                "information": "Fashion post about sustainable clothing",
                "metadata": {
                    "caption": "🌿 Sustainable fashion isn't just a trend—it's a necessity! Here are 5 ways to build an eco-friendly wardrobe: 1) Buy quality pieces that last 2) Choose natural fabrics 3) Support ethical brands 4) Shop secondhand 5) Take care of what you own #SustainableFashion #EcoFriendly #SlowFashion",
                    "platform": "instagram",
                    "category": "fashion",
                    "test_id": "test_store_1"
                }
            },
            {
                "information": "Mental health awareness post with self-care tips",
                "metadata": {
                    "caption": "Mental Health Monday 🧠💚 Remember: It's okay to not be okay. Taking care of your mental health is just as important as taking care of your physical health. Try these simple self-care practices: • Take deep breaths • Go for a walk • Talk to someone you trust • Practice gratitude #MentalHealthAwareness #SelfCare #YouMatter",
                    "platform": "instagram", 
                    "category": "wellness",
                    "test_id": "test_store_2"
                }
            }
        ]
        
        stored_count = 0
        
        for i, data in enumerate(test_data):
            try:
                store_message = {
                    "jsonrpc": "2.0",
                    "id": f"store-{i+1}",
                    "method": "tools/call",
                    "params": {
                        "name": "store",
                        "arguments": {
                            "information": data["information"],
                            "metadata": json.dumps(data["metadata"])
                        }
                    }
                }
                
                async with self.session.post(
                    f"{self.server_url}/message",
                    json=store_message,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "error" not in result:
                            stored_count += 1
                            logger.info(f"✓ Store operation {i+1} successful")
                        else:
                            logger.error(f"✗ Store operation {i+1} failed: {result.get('error')}")
                    else:
                        logger.error(f"✗ Store operation {i+1} HTTP error: {response.status}")
                        
            except Exception as e:
                logger.error(f"✗ Store operation {i+1} exception: {e}")
        
        success = stored_count == len(test_data)
        logger.info(f"Store functionality: {stored_count}/{len(test_data)} successful")
        self.test_results['store_functionality'] = success
        return success
    
    async def test_find_functionality(self) -> bool:
        """Test find operation with query prefix validation."""
        logger.info("Testing find functionality...")
        
        test_queries = [
            "sustainable fashion tips",
            "mental health self-care",
            "eco-friendly lifestyle advice",
            "wellness and mindfulness practices"
        ]
        
        successful_queries = 0
        
        for i, query in enumerate(test_queries):
            try:
                find_message = {
                    "jsonrpc": "2.0",
                    "id": f"find-{i+1}",
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
                    json=find_message,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "error" not in result and "result" in result:
                            content = result.get("result", {}).get("content", [])
                            if content:
                                successful_queries += 1
                                logger.info(f"✓ Find query {i+1} successful: '{query}' -> {len(content)} results")
                            else:
                                logger.info(f"⚠ Find query {i+1} returned no results: '{query}'")
                        else:
                            logger.error(f"✗ Find query {i+1} failed: {result.get('error', 'Unknown error')}")
                    else:
                        logger.error(f"✗ Find query {i+1} HTTP error: {response.status}")
                        
            except Exception as e:
                logger.error(f"✗ Find query {i+1} exception: {e}")
            
            # Small delay between queries
            await asyncio.sleep(0.5)
        
        success = successful_queries > 0
        logger.info(f"Find functionality: {successful_queries}/{len(test_queries)} successful queries")
        self.test_results['find_functionality'] = success
        return success
    
    async def test_embedding_quality(self) -> bool:
        """Test embedding quality by checking semantic similarity."""
        logger.info("Testing embedding quality...")
        
        # Store a test item and then search for it with semantic variations
        test_item = {
            "information": "Photography tips for travel bloggers",
            "metadata": {
                "caption": "📸 Travel Photography Tips for Beginners: 1) Golden hour lighting 2) Rule of thirds composition 3) Capture local culture 4) Pack light gear 5) Edit on mobile apps #TravelPhotography #Photography #Travel #Blogger",
                "platform": "instagram",
                "category": "photography",
                "test_id": "embedding_quality_test"
            }
        }
        
        try:
            # Store test item
            store_message = {
                "jsonrpc": "2.0",
                "id": "embedding-store",
                "method": "tools/call",
                "params": {
                    "name": "store",
                    "arguments": {
                        "information": test_item["information"],
                        "metadata": json.dumps(test_item["metadata"])
                    }
                }
            }
            
            async with self.session.post(
                f"{self.server_url}/message",
                json=store_message,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    logger.error("Failed to store test item for embedding quality test")
                    self.test_results['embedding_quality'] = False
                    return False
            
            # Wait a moment for indexing
            await asyncio.sleep(2)
            
            # Search with semantic variations
            semantic_queries = [
                "photography advice for travelers",  # Direct match
                "camera tips for bloggers",  # Related terms
                "taking pictures while traveling",  # Different phrasing
            ]
            
            relevant_results = 0
            
            for query in semantic_queries:
                find_message = {
                    "jsonrpc": "2.0",
                    "id": f"embedding-find",
                    "method": "tools/call",
                    "params": {
                        "name": "find",
                        "arguments": {
                            "query": query,
                            "limit": 3
                        }
                    }
                }
                
                async with self.session.post(
                    f"{self.server_url}/message",
                    json=find_message,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("result", {}).get("content", [])
                        
                        # Check if our test item appears in results
                        for item in content:
                            if "embedding_quality_test" in str(item):
                                relevant_results += 1
                                logger.info(f"✓ Semantic query found relevant result: '{query}'")
                                break
            
            success = relevant_results > 0
            logger.info(f"Embedding quality: {relevant_results}/{len(semantic_queries)} semantic matches")
            self.test_results['embedding_quality'] = success
            return success
            
        except Exception as e:
            logger.error(f"✗ Embedding quality test error: {e}")
            self.test_results['embedding_quality'] = False
            return False

    def print_summary(self):
        """Print comprehensive test summary."""
        logger.info("\n" + "="*60)
        logger.info("INTEGRATION TEST SUMMARY")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"{test_name:<25} {status}")
        
        logger.info("-" * 60)
        logger.info(f"Total: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED! MCP Server is ready for production.")
        else:
            logger.error("❌ Some tests failed. Please check the configuration and logs.")
        
        return passed_tests == total_tests

async def main():
    """Run comprehensive integration tests."""
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
    
    logger.info("Starting MCP Server Integration Tests")
    logger.info(f"Server URL: {server_url}")
    logger.info("="*60)
    
    async with MCPIntegrationTester(server_url) as tester:
        # Wait for server with extended timeout for model loading
        if not tester.wait_for_server(timeout=120):
            logger.error("Server not ready - aborting tests")
            return False
        
        # Run tests in sequence
        tests = [
            ("MCP Initialization", tester.test_mcp_initialize),
            ("Tool Availability", tester.test_tools_available),
            ("Store Functionality", tester.test_store_functionality),
            ("Find Functionality", tester.test_find_functionality),
            ("Embedding Quality", tester.test_embedding_quality),
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n--- {test_name} ---")
            await test_func()
            await asyncio.sleep(1)  # Brief pause between tests
        
        # Print final summary
        return tester.print_summary()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
