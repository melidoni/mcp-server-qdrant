import logging
import os
from mcp_server_qdrant.mcp_server import QdrantMCPServer
from mcp_server_qdrant.settings import QdrantSettings, ToolSettings
from mcp_server_qdrant.embeddings.base import EmbeddingProvider
from fastembed import TextEmbedding
from fastembed.common.model_description import PoolingType, ModelSource
import asyncio

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CustomFastEmbedProvider(EmbeddingProvider):
    """Custom FastEmbed provider that registers and uses the multilingual-e5-large-instruct model."""
    
    def __init__(self, model_name: str, hf_model_id: str, vector_dimension: int, cache_dir: str = None):
        self.model_name = model_name
        self.hf_model_id = hf_model_id
        self.vector_dimension = vector_dimension
        self.cache_dir = cache_dir
        
        # Query prefix for embedding model consistency - configurable via environment
        self.query_prefix = os.getenv(
            "EMBEDDING_QUERY_PREFIX", 
            "Instruct: Given a query of a social media caption, find other social media captions that are most relevant. Query: "
        )
        
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
        return os.getenv("QDRANT_VECTOR_NAME", "text_dense")
    
    def get_vector_size(self) -> int:
        """Get the size of the vector for the Qdrant collection."""
        return self.vector_dimension

# Custom tool descriptions for social media
SOCIAL_MEDIA_SEARCH_DESCRIPTION = os.getenv(
    "TOOL_FIND_DESCRIPTION",
    """Search for relevant social media posts based on natural language descriptions. 
The 'query' parameter should describe what you're looking for, and the tool will return the most relevant social media posts. 
Use this when you need to find existing social media posts for reference or to identify similar content."""
)

SOCIAL_MEDIA_STORE_DESCRIPTION = os.getenv(
    "TOOL_STORE_DESCRIPTION", 
    """Store social media posts for later retrieval. 
The 'information' parameter should contain a natural language description of what the social media post is about, 
while the actual social media post content should be included in the 'metadata' parameter. 
Use this whenever you want to store a social media post for future searching."""
)

# Create settings
tool_settings = ToolSettings()
tool_settings.tool_find_description = SOCIAL_MEDIA_SEARCH_DESCRIPTION
tool_settings.tool_store_description = SOCIAL_MEDIA_STORE_DESCRIPTION

qdrant_settings = QdrantSettings()
qdrant_settings.location = os.getenv("QDRANT_URL")
qdrant_settings.api_key = os.getenv("QDRANT_API_KEY")
qdrant_settings.collection_name = os.getenv("COLLECTION_NAME", "social_media")
qdrant_settings.search_limit = int(os.getenv("QDRANT_SEARCH_LIMIT", "10"))
qdrant_settings.read_only = os.getenv("QDRANT_READ_ONLY", "false").lower() == "true"

logger.info(f"Qdrant settings: URL={qdrant_settings.location}, Collection={qdrant_settings.collection_name}")
logger.info(f"Search limit: {qdrant_settings.search_limit}, Read only: {qdrant_settings.read_only}")

# Create custom embedding provider with model registration
embedding_provider = CustomFastEmbedProvider(
    model_name="multilingual-e5-large-instruct",
    hf_model_id="intfloat/multilingual-e5-large-instruct", 
    vector_dimension=1024,
    cache_dir="/mnt/mcp_model"
)

logger.info(f"Embedding model: multilingual-e5-large-instruct (HF: intfloat/multilingual-e5-large-instruct)")
logger.info(f"Vector dimension: 1024, Cache dir: /mnt/mcp_model")

# Create MCP server
logger.info("Creating MCP server...")
mcp = QdrantMCPServer(
    tool_settings=tool_settings,
    qdrant_settings=qdrant_settings,
    embedding_provider=embedding_provider,
)

logger.info("MCP server created successfully!")
