import asyncio
import logging
import os
from pathlib import Path

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
        
        # Check cache status before initialization
        self._check_cache_status()
        
        # Register custom model if HuggingFace model ID is provided
        if self.hf_model_id:
            self._register_custom_model()
        
        # Create the embedding model
        logger.info(f"Initializing TextEmbedding with cache_dir: {self.cache_dir}")
        self.embedding_model = TextEmbedding(
            model_name=self.model_name,
            cache_dir=self.cache_dir
        )
        
        # Log post-initialization cache status
        self._log_post_init_status()
        
    def _check_cache_status(self):
        """Check and log the current cache status."""
        cache_path = Path(self.cache_dir)
        logger.info(f"🔍 Cache directory: {cache_path}")
        logger.info(f"🔍 Cache exists: {cache_path.exists()}")
        
        if cache_path.exists():
            # Check for model-specific cache
            model_cache_name = f"models--{self.hf_model_id.replace('/', '--')}" if self.hf_model_id else f"models--intfloat--{self.model_name}"
            model_cache_path = cache_path / model_cache_name
            
            logger.info(f"🎯 Model cache path: {model_cache_path}")
            logger.info(f"🎯 Model cache exists: {model_cache_path.exists()}")
            
            if model_cache_path.exists():
                # Check for required files
                refs_main = model_cache_path / "refs" / "main"
                snapshots_dir = model_cache_path / "snapshots"
                
                logger.info(f"   ✅ refs/main exists: {refs_main.exists()}")
                logger.info(f"   📁 snapshots dir exists: {snapshots_dir.exists()}")
                
                if snapshots_dir.exists():
                    snapshots = list(snapshots_dir.iterdir())
                    logger.info(f"   📊 Found {len(snapshots)} snapshots")
                    
                    for snapshot in snapshots:
                        if snapshot.is_dir():
                            # Check both direct ONNX files and onnx subdirectory
                            direct_onnx = list(snapshot.glob("*.onnx*"))
                            onnx_subdir = snapshot / "onnx"
                            subdir_onnx = list(onnx_subdir.glob("*.onnx*")) if onnx_subdir.exists() else []
                            total_onnx = len(direct_onnx) + len(subdir_onnx)
                            
                            logger.info(f"      📄 Snapshot {snapshot.name}: {total_onnx} ONNX files")
                            if subdir_onnx:
                                logger.info(f"         📁 onnx/ subdirectory: {len(subdir_onnx)} files")
                                for onnx_file in subdir_onnx:
                                    size_mb = onnx_file.stat().st_size / (1024*1024) if onnx_file.exists() else 0
                                    logger.info(f"            📄 {onnx_file.name} ({size_mb:.1f} MB)")
                            if direct_onnx:
                                logger.info(f"         📄 Direct ONNX files: {len(direct_onnx)} files")
        else:
            logger.warning(f"❌ Cache directory does not exist: {cache_path}")

    def _register_custom_model(self):
        """Register a custom model with FastEmbed."""
        try:
            logger.info(f"Registering custom model: {self.model_name}")
            logger.info(f"Using HuggingFace model ID: {self.hf_model_id}")
            
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

    def _log_post_init_status(self):
        """Log cache status after model initialization."""
        logger.info("📊 Post-initialization cache status:")
        cache_path = Path(self.cache_dir)
        
        if cache_path.exists():
            try:
                # Count total files and size
                total_files = sum(1 for _ in cache_path.rglob("*") if _.is_file())
                total_size = sum(f.stat().st_size for f in cache_path.rglob("*") if f.is_file())
                
                logger.info(f"   📁 Total files in cache: {total_files}")
                logger.info(f"   💾 Total cache size: {total_size:,} bytes ({total_size / (1024**3):.2f} GB)")
                
                # Look for model directories
                model_dirs = [d for d in cache_path.iterdir() if d.is_dir() and "models--" in d.name]
                logger.info(f"   🤖 Model directories: {len(model_dirs)}")
                
                for model_dir in model_dirs:
                    logger.info(f"      📁 {model_dir.name}")
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Error reading cache contents: {e}")
        else:
            logger.warning("   ❌ Cache directory still does not exist after initialization")

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
