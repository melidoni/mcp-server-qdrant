import logging
import os
from mcp_server_qdrant.mcp_server import QdrantMCPServer
from mcp_server_qdrant.settings import QdrantSettings, ToolSettings
from mcp_server_qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.qdrant import QdrantService
from fastembed import TextEmbedding
from fastembed.common.model_description import DenseModelDescription, PoolingType, ModelSource
from qdrant_client.http.models import NamedVector
import asyncio

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CustomFastEmbedProvider(EmbeddingProvider):
    """
    Custom FastEmbed provider that can register and use custom models.
    """
    
    def __init__(self, model_name: str, hf_model_id: str, vector_dimension: int, cache_dir: str = None):
        self.model_name = model_name
        self.hf_model_id = hf_model_id
        self.vector_dimension = vector_dimension
        self.cache_dir = cache_dir
        
        # Query prefix for embedding model consistency
        self.query_prefix = "Instruct: Given a query of a social media caption, find other social media captions that are most relevant. Query: "
        
        # Register the custom model
        self._register_custom_model()
        
        # Create the embedding model
        self.embedding_model = TextEmbedding(
            model_name=self.model_name,
            cache_dir=self.cache_dir
        )
        
    def _register_custom_model(self):
        """Register a custom model with FastEmbed."""
        try:
            logger.info(f"Registering custom model: {self.model_name}")
            
            # Create model source from HuggingFace
            model_source = ModelSource(hf=self.hf_model_id)
            
            # Register the custom model
            TextEmbedding.add_custom_model(
                model=self.model_name,
                pooling=PoolingType.MEAN,
                normalization=True,
                sources=model_source,
                dim=self.vector_dimension,
                model_file="onnx/model.onnx",
                additional_files=["onnx/model.onnx_data"],
            )
            
            logger.info(f"Successfully registered custom model '{self.model_name}'")
            
        except Exception as e:
            logger.error(f"Failed to register custom model '{self.model_name}': {e}")
            raise
    
    async def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """Embed a list of documents into vectors."""
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: list(self.embedding_model.passage_embed(documents))
        )
        return [embedding.tolist() for embedding in embeddings]
    
    async def embed_query(self, query: str) -> list[float]:
        """Embed a query into a vector with prefix."""
        # Apply the query prefix like the original Qdrant service
        prefixed_query = f"{self.query_prefix}{query}"
        
        # Log the prefixed query for verification
        logger.info(f"Embedding query with prefix: '{prefixed_query[:100]}...'")
        
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, lambda: list(self.embedding_model.query_embed([prefixed_query]))
            )
            result = embeddings[0].tolist()
            logger.info(f"Successfully embedded query, vector size: {len(result)}")
            return result
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise
    
    def get_vector_name(self) -> str:
        """Return the name of the vector for the Qdrant collection."""
        # Use the existing collection's vector name to maintain compatibility
        vector_name = "text_dense"
        logger.info(f"Using vector name: {vector_name}")
        return vector_name
    
    def get_vector_size(self) -> int:
        """Get the size of the vector for the Qdrant collection."""
        return self.vector_dimension

class CustomQdrantService(QdrantService):
    """Custom Qdrant service that uses the search method instead of query_points."""
    
    async def search(self, query: str, *, collection_name: str | None = None, limit: int = 10, query_filter = None):
        """
        Override the search method to use client.search() with NamedVector like the agent does.
        """
        from mcp_server_qdrant.qdrant import Entry
        
        collection_name = collection_name or self._default_collection_name
        collection_exists = await self._client.collection_exists(collection_name)
        if not collection_exists:
            return []

        # Embed the query
        query_vector = await self._embedding_provider.embed_query(query)
        
        # Use the same search method as the agent
        search_results = await self._client.search(
            collection_name=collection_name,
            query_vector=NamedVector(name="text_dense", vector=query_vector),
            limit=limit,
            with_payload=True,
            with_vectors=False
        )

        return [
            Entry(
                content=result.payload["document"],
                metadata=result.payload.get("metadata"),
            )
            for result in search_results
        ]

# Create custom embedding provider
logger.info("Creating custom embedding provider...")
embedding_provider = CustomFastEmbedProvider(
    model_name="multilingual-e5-large-instruct",
    hf_model_id="intfloat/multilingual-e5-large-instruct",
    vector_dimension=1024,
    cache_dir="/mnt/mcp_model"
)

# Create settings with environment variables
qdrant_settings = QdrantSettings()
tool_settings = ToolSettings()

logger.info(f"Qdrant settings: URL={qdrant_settings.location}, Collection={qdrant_settings.collection_name}")

# Create custom Qdrant service that uses the search method
qdrant_service = CustomQdrantService(
    qdrant_settings=qdrant_settings,
    embedding_provider=embedding_provider,
    field_indexes=[]
)

# Create MCP server with custom service
logger.info("Creating MCP server...")
mcp = QdrantMCPServer(
    tool_settings=tool_settings,
    qdrant_settings=qdrant_settings,
    embedding_provider=embedding_provider,
)

# Replace the default qdrant service with our custom one
mcp._qdrant_service = qdrant_service

logger.info("MCP server created successfully!")

# Start the server
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting MCP server with SSE transport on {host}:{port}...")
    mcp.run(transport="sse", host=host, port=port)
