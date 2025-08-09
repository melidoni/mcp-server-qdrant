# MCP Server Local Testing Plan

## Overview
This document provides a comprehensive plan for testing the remote MCP server locally using Docker, including custom embedding model initialization and Qdrant connection validation.

## Current Configuration Analysis

### Remote MCP Server Configuration (from Cloud Run)
- **Qdrant URL**: `https://0e76560f-4158-4cac-b41e-eb9830d1755f.us-east4-0.gcp.cloud.qdrant.io`
- **Custom Model**: `multilingual-e5-large-instruct` (1024 dimensions)
- **HuggingFace Model ID**: `intfloat/multilingual-e5-large-instruct`
- **Query Prefix**: `"Instruct: Given a query of a social media caption, find other social media captions that are most relevant. Query: "`
- **Collection**: `social_media` (inferred from agent configuration)
- **Vector Name**: `text_dense`
- **Transport**: SSE on port 8080
- **Model Cache**: `/mnt/mcp_model`

## Testing Setup Files

### 1. Environment Configuration File

**File**: `qdrant-mcp-server/.env.local`
```bash
# Local Testing Environment Configuration for MCP Server
# Replace YOUR_QDRANT_API_KEY with your actual API key

# MCP Server Configuration
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8080

# Qdrant Configuration (Remote)
QDRANT_URL=https://0e76560f-4158-4cac-b41e-eb9830d1755f.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY="API_KEY"
COLLECTION_NAME=social_media

# Tool Descriptions (matching production)
TOOL_FIND_DESCRIPTION=Search for relevant social media posts based on natural language descriptions. The 'query' parameter should describe what you're looking for, and the tool will return the most relevant social media posts. The system will automatically add the prefix 'Instruct: Given a query of a social media caption, find other social media captions that are most relevant. Query: ' to your query before searching. Use this when you need to find existing social media posts for reference or to identify patterns.
TOOL_STORE_DESCRIPTION=Store social media posts for later retrieval. The 'information' parameter should contain a natural language description of what the social media post is about, while the actual social media post content (e.g., the caption text) should be included in the 'metadata' parameter as a 'caption' property. The value of 'metadata' is a Python dictionary with strings as keys. Use this whenever you want to store a social media post for future searching.

# Model Cache Directory
MODEL_CACHE_DIR=/mnt/mcp_model

# Logging Configuration
PYTHONUNBUFFERED=1
LOG_LEVEL=DEBUG
```

### 2. Docker Compose Configuration

**File**: `qdrant-mcp-server/docker-compose.test.yml`
```yaml
version: '3.8'

services:
  mcp-server-test:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    env_file:
      - .env.local
    volumes:
      # Model cache volume (local directory)
      - ./model_cache:/mnt/mcp_model
      # Logs volume for easier access
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    
  # Optional: Local MCP client for testing
  mcp-client-test:
    image: python:3.11-slim
    depends_on:
      - mcp-server-test
    volumes:
      - ./tests:/app/tests
      - ./client_scripts:/app/scripts
    working_dir: /app
    command: tail -f /dev/null  # Keep container running for manual testing
    environment:
      - MCP_SERVER_URL=http://mcp-server-test:8080
```

### 3. Testing Scripts

#### A. Initialization Test Script

**File**: `qdrant-mcp-server/tests/test_initialization.py`
```python
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
```

#### B. Embedding Model Test Script

**File**: `qdrant-mcp-server/tests/test_embedding_model.py`
```python
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
        # Test store operation first
        logger.info("\n=== Testing Store Operation ===")
        store_result = await tester.test_store_operation(
            test_store_data["information"], 
            test_store_data["metadata"]
        )
        
        # Test embedding queries
        logger.info("\n=== Testing Embedding Queries ===")
        for query in test_queries:
            logger.info(f"\nTesting query: '{query}'")
            await tester.test_embedding_query(query)
            await asyncio.sleep(1)  # Small delay between queries
        
        # Summary
        logger.info("\n=== Test Summary ===")
        logger.info(f"Store Operation: {'✓' if 'error' not in store_result else '✗'}")
        logger.info("Query Operations: See individual results above")

if __name__ == "__main__":
    asyncio.run(main())
```

#### C. Qdrant Connection Test Script

**File**: `qdrant-mcp-server/tests/test_qdrant_connection.py`
```python
#!/usr/bin/env python3
"""
Test script to verify Qdrant connection and collection access.
"""

import asyncio
import logging
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QdrantConnectionTester:
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("COLLECTION_NAME", "social_media")
        
        if not self.qdrant_url or not self.qdrant_api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set")
        
        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key
        )
    
    def test_connection(self) -> bool:
        """Test basic connection to Qdrant."""
        try:
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant successfully. Found {len(collections.collections)} collections")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            return False
    
    def test_collection_exists(self) -> bool:
        """Test if the target collection exists."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' found with {collection_info.points_count} points")
            logger.info(f"Vector configuration: {collection_info.config.params.vectors}")
            return True
        except Exception as e:
            logger.error(f"Collection '{self.collection_name}' not found or inaccessible: {e}")
            return False
    
    def test_search_capability(self) -> bool:
        """Test basic search capability."""
        try:
            # Use a dummy vector of the right size (1024 dimensions for multilingual-e5-large-instruct)
            dummy_vector = [0.1] * 1024
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=("text_dense", dummy_vector),
                limit=3,
                with_payload=True
            )
            
            logger.info(f"Search test successful. Retrieved {len(results)} results")
            for i, result in enumerate(results):
                logger.info(f"Result {i+1}: Score {result.score:.4f}")
            
            return True
        except Exception as e:
            logger.error(f"Search capability test failed: {e}")
            return False

def main():
    """Run Qdrant connection tests."""
    logger.info("Starting Qdrant Connection Tests")
    
    try:
        tester = QdrantConnectionTester()
        
        # Test connection
        logger.info("\n=== Testing Qdrant Connection ===")
        connection_success = tester.test_connection()
        
        # Test collection existence
        logger.info("\n=== Testing Collection Access ===")
        collection_success = tester.test_collection_exists()
        
        # Test search capability
        if collection_success:
            logger.info("\n=== Testing Search Capability ===")
            search_success = tester.test_search_capability()
        else:
            search_success = False
        
        # Summary
        logger.info("\n=== Test Summary ===")
        logger.info(f"Qdrant Connection: {'✓' if connection_success else '✗'}")
        logger.info(f"Collection Access: {'✓' if collection_success else '✗'}")
        logger.info(f"Search Capability: {'✓' if search_success else '✗'}")
        
    except Exception as e:
        logger.error(f"Test setup failed: {e}")

if __name__ == "__main__":
    main()
```

### 4. Testing Makefile

**File**: `qdrant-mcp-server/Makefile`
```makefile
# MCP Server Local Testing Makefile

.PHONY: help setup test-env build up down logs test-init test-embedding test-qdrant test-all clean

# Default target
help:
	@echo "MCP Server Local Testing Commands:"
	@echo "  setup         - Set up testing environment"
	@echo "  build         - Build Docker image"
	@echo "  up            - Start MCP server with Docker Compose"
	@echo "  down          - Stop MCP server"
	@echo "  logs          - Show server logs"
	@echo "  test-init     - Test server initialization"
	@echo "  test-embedding - Test embedding model functionality"
	@echo "  test-qdrant   - Test Qdrant connection"
	@echo "  test-all      - Run all tests"
	@echo "  clean         - Clean up testing artifacts"

# Setup testing environment
setup:
	@echo "Setting up testing environment..."
	@mkdir -p model_cache logs tests client_scripts
	@echo "Created directories: model_cache, logs, tests, client_scripts"
	@echo "Please create .env.local file with your configuration"

# Build Docker image
build:
	@echo "Building MCP server Docker image..."
	docker-compose -f docker-compose.test.yml build

# Start services
up:
	@echo "Starting MCP server..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Server starting... Check logs with 'make logs'"

# Stop services
down:
	@echo "Stopping MCP server..."
	docker-compose -f docker-compose.test.yml down

# Show logs
logs:
	docker-compose -f docker-compose.test.yml logs -f mcp-server-test

# Test server initialization
test-init:
	@echo "Testing server initialization..."
	docker-compose -f docker-compose.test.yml exec mcp-client-test python /app/tests/test_initialization.py

# Test embedding model
test-embedding:
	@echo "Testing embedding model functionality..."
	docker-compose -f docker-compose.test.yml exec mcp-client-test python /app/tests/test_embedding_model.py

# Test Qdrant connection
test-qdrant:
	@echo "Testing Qdrant connection..."
	python tests/test_qdrant_connection.py

# Run all tests
test-all: test-qdrant test-init test-embedding
	@echo "All tests completed!"

# Clean up
clean:
	@echo "Cleaning up testing artifacts..."
	docker-compose -f docker-compose.test.yml down -v
	docker system prune -f
	rm -rf logs/* model_cache/*
```

## Testing Procedures

### Phase 1: Environment Setup
1. **Create Environment File**: Create `.env.local` with your Qdrant API key
2. **Set up Directory Structure**: Run `make setup`
3. **Build Docker Image**: Run `make build`

### Phase 2: Basic Connectivity Tests
1. **Test Qdrant Connection**: Run `make test-qdrant`
2. **Start MCP Server**: Run `make up`
3. **Monitor Startup**: Run `make logs`

### Phase 3: MCP Server Tests
1. **Test Initialization**: Run `make test-init`
2. **Test Embedding Model**: Run `make test-embedding`
3. **Comprehensive Testing**: Run `make test-all`

### Phase 4: Performance & Model Validation
1. **Monitor Model Loading**: Check logs for custom model registration
2. **Validate Embedding Quality**: Test with various query types
3. **Performance Testing**: Monitor response times and resource usage

## Expected Results

### Successful Initialization Indicators
- ✅ Custom model `multilingual-e5-large-instruct` registered successfully
- ✅ Qdrant connection established
- ✅ SSE transport listening on port 8080
- ✅ MCP tools (`find`, `store`) available
- ✅ Query prefix applied correctly

### Key Log Messages to Look For
```
INFO: Successfully registered custom model 'multilingual-e5-large-instruct'
INFO: Starting MCP server with SSE transport on 0.0.0.0:8080...
INFO: Embedding query with prefix: 'Instruct: Given a query of a social media caption...'
INFO: MCP server created successfully!
```

## Troubleshooting Guide

### Common Issues
1. **Model Loading Fails**: Check `/mnt/mcp_model` directory permissions and disk space
2. **Qdrant Connection Issues**: Verify API key and URL in `.env.local`
3. **SSE Connection Problems**: Check port 8080 availability
4. **Memory Issues**: Custom model requires significant RAM (>4GB recommended)

### Debug Commands
```bash
# Check container logs
make logs

# Check container health
docker-compose -f docker-compose.test.yml ps

# Interactive debugging
docker-compose -f docker-compose.test.yml exec mcp-server-test bash
```

## Next Steps
After completing this testing plan, you'll be ready to:
1. Deploy with confidence to Cloud Run
2. Integrate with your policy agent
3. Scale the MCP server as needed
4. Monitor performance in production
