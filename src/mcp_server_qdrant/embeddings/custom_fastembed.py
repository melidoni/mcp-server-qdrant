import asyncio
import logging
import os

from fastembed import TextEmbedding
from fastembed.common.model_description import DenseModelDescription, PoolingType, ModelSource

from mcp_server_qdrant.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class CustomFastEmbedProvider(EmbeddingProvider):
    """
    Custom FastEmbed implementation with support for custom model registration
    and query prefix functionality for social media embeddings.
    """

    def __init__(self, model_name: str, hf_model_id: str = None, cache_dir: str = None, query_prefix: str = None):
        self.model_name = model_name
        self.hf_model_id = hf_model_id
        self.cache_dir = cache_dir or os.getenv("MODEL_CACHE_DIR", "/mnt/mcp_model")
        
        # Query prefix for embedding model consistency
        self.query_prefix = query_prefix or "Instruct: Given a query of a social media caption, find other social media captions that are most relevant. Query: "
        
        # Register custom model if HuggingFace model ID is provided
        if self.hf_model_id:
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
            
            # Get vector dimension from model name mapping
            vector_dimension = self._get_vector_dimension()
            
            # Register the custom model
            TextEmbedding.add_custom_model(
                model=self.model_name,
                pooling=PoolingType.MEAN,
                normalization=True,
                sources=model_source,
                dim=vector_dimension,
                model_file="onnx/model.onnx",
                additional_files=["onnx/model.onnx_data"],
            )
            
            logger.info(f"Successfully registered custom model '{self.model_name}'")
            
        except Exception as e:
            logger.error(f"Failed to register custom model '{self.model_name}': {e}")
            raise

    def _get_vector_dimension(self) -> int:
        """Get vector dimension based on model name."""
        # Model dimension mapping
        model_dimensions = {
            "multilingual-e5-large-instruct": 1024,
            "multilingual-e5-base": 768,
            "multilingual-e5-small": 384,
        }
        
        return model_dimensions.get(self.model_name, 1024)  # Default to 1024

    async def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """Embed a list of documents into vectors."""
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: list(self.embedding_model.passage_embed(documents))
        )
        return [embedding.tolist() for embedding in embeddings]

    async def embed_query(self, query: str) -> list[float]:
        """Embed a query into a vector with optional prefix."""
        # Apply the query prefix if configured
        if self.query_prefix:
            prefixed_query = f"{self.query_prefix}{query}"
            logger.debug(f"Embedding query with prefix: '{prefixed_query[:100]}...'")
        else:
            prefixed_query = query
            
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: list(self.embedding_model.query_embed([prefixed_query]))
        )
        return embeddings[0].tolist()

    def get_vector_name(self) -> str:
        """Return the name of the vector for the Qdrant collection."""
        # Use a standard name that matches existing collections
        return "text_dense"

    def get_vector_size(self) -> int:
        """Get the size of the vector for the Qdrant collection."""
        try:
            model_description: DenseModelDescription = (
                self.embedding_model._get_model_description(self.model_name)
            )
            return model_description.dim
        except Exception:
            # Fallback to configured dimension
            return self._get_vector_dimension()
