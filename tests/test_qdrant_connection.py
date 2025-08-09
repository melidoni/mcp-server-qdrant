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
            for collection in collections.collections:
                logger.info(f"  - Collection: {collection.name}")
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
            
            # Check if the expected vector name exists
            vectors = collection_info.config.params.vectors
            if isinstance(vectors, dict) and "text_dense" in vectors:
                vector_config = vectors["text_dense"]
                logger.info(f"Vector 'text_dense' found with {vector_config.size} dimensions")
                
                if vector_config.size == 1024:
                    logger.info("✓ Vector dimensions match expected size for multilingual-e5-large-instruct")
                else:
                    logger.warning(f"⚠ Vector dimensions ({vector_config.size}) don't match expected 1024")
            else:
                logger.warning("⚠ Expected vector 'text_dense' not found in collection")
                
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
                if result.payload:
                    # Show some payload fields
                    payload_preview = {k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                                     for k, v in list(result.payload.items())[:3]}
                    logger.info(f"  Payload preview: {payload_preview}")
            
            return True
        except Exception as e:
            logger.error(f"Search capability test failed: {e}")
            return False

    def get_collection_stats(self) -> dict:
        """Get detailed collection statistics."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            stats = {
                "name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "status": collection_info.status.name,
                "config": {
                    "distance": collection_info.config.params.vectors.get("text_dense", {}).distance.name if hasattr(collection_info.config.params.vectors.get("text_dense", {}), 'distance') else "unknown",
                    "vector_size": collection_info.config.params.vectors.get("text_dense", {}).size if hasattr(collection_info.config.params.vectors.get("text_dense", {}), 'size') else 0
                }
            }
            logger.info(f"Collection stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}

def main():
    """Run Qdrant connection tests."""
    logger.info("Starting Qdrant Connection Tests")
    logger.info(f"QDRANT_URL: {os.getenv('QDRANT_URL', 'Not set')}")
    logger.info(f"COLLECTION_NAME: {os.getenv('COLLECTION_NAME', 'social_media')}")
    
    try:
        tester = QdrantConnectionTester()
        
        # Test connection
        logger.info("\n=== Testing Qdrant Connection ===")
        connection_success = tester.test_connection()
        
        # Test collection existence
        logger.info("\n=== Testing Collection Access ===")
        collection_success = tester.test_collection_exists()
        
        # Get collection stats
        if collection_success:
            logger.info("\n=== Collection Statistics ===")
            stats = tester.get_collection_stats()
        
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
        
        if connection_success and collection_success and search_success:
            logger.info("\n🎉 All Qdrant tests passed! Ready for MCP server testing.")
        else:
            logger.error("\n❌ Some Qdrant tests failed. Please check configuration.")
        
    except Exception as e:
        logger.error(f"Test setup failed: {e}")

if __name__ == "__main__":
    main()
