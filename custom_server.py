import logging
from mcp_server_qdrant.mcp_server import QdrantMCPServer
from mcp_server_qdrant.settings import QdrantSettings, ToolSettings
from mcp_server_qdrant.embeddings.base import EmbeddingProvider
from fastembed import TextEmbedding
from fastembed.common.model_description import DenseModelDescription, PoolingType, ModelSource
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
        
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: list(self.embedding_model.query_embed([prefixed_query]))
        )
        return embeddings[0].tolist()
    
    def get_vector_name(self) -> str:
        """Return the name of the vector for the Qdrant collection."""
        # Use the existing collection's vector name to maintain compatibility
        return "text_dense"
    
    def get_vector_size(self) -> int:
        """Get the size of the vector for the Qdrant collection."""
        return self.vector_dimension

# Create custom embedding provider
logger.info("Creating custom embedding provider...")
embedding_provider = CustomFastEmbedProvider(
    model_name="multilingual-e5-large-instruct",
    hf_model_id="intfloat/multilingual-e5-large-instruct",
    vector_dimension=1024,
    cache_dir="/mnt/mcp_model"
)

# Create MCP server with custom provider
logger.info("Creating MCP server...")
mcp = QdrantMCPServer(
    tool_settings=ToolSettings(),
    qdrant_settings=QdrantSettings(),
    embedding_provider=embedding_provider,
)

logger.info("MCP server created successfully!")

# Start the server
if __name__ == "__main__":
    logger.info("Starting MCP server with SSE transport...")
    mcp.run(transport="sse", host="0.0.0.0", port=8080)
