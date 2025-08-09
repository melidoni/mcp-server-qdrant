import os
from mcp_server_qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.embeddings.types import EmbeddingProviderType
from mcp_server_qdrant.settings import EmbeddingProviderSettings


def create_embedding_provider(settings: EmbeddingProviderSettings) -> EmbeddingProvider:
    """
    Create an embedding provider based on the specified type.
    :param settings: The settings for the embedding provider.
    :return: An instance of the specified embedding provider.
    """
    if settings.provider_type == EmbeddingProviderType.FASTEMBED:
        from mcp_server_qdrant.embeddings.fastembed import FastEmbedProvider

        return FastEmbedProvider(settings.model_name)
    
    elif settings.provider_type == EmbeddingProviderType.CUSTOM_FASTEMBED:
        from mcp_server_qdrant.embeddings.custom_fastembed import CustomFastEmbedProvider

        # Get additional configuration from environment variables
        hf_model_id = os.getenv("CUSTOM_HF_MODEL_ID")
        cache_dir = os.getenv("MODEL_CACHE_DIR", "/mnt/mcp_model")
        query_prefix = os.getenv("CUSTOM_QUERY_PREFIX")
        
        return CustomFastEmbedProvider(
            model_name=settings.model_name,
            hf_model_id=hf_model_id,
            cache_dir=cache_dir,
            query_prefix=query_prefix
        )
    
    else:
        raise ValueError(f"Unsupported embedding provider: {settings.provider_type}")
