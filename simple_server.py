import logging
import os
from mcp_server_qdrant.mcp_server import QdrantMCPServer
from mcp_server_qdrant.settings import QdrantSettings, ToolSettings, EmbeddingProviderSettings
from mcp_server_qdrant.embeddings.fastembed import FastEmbedProvider

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CustomFastEmbedProvider(FastEmbedProvider):
    """Custom FastEmbed provider that returns 'text_dense' as vector name for collection compatibility."""
    
    def get_vector_name(self) -> str:
        """Return the name of the vector for the Qdrant collection."""
        return "text_dense"

# Custom tool descriptions from environment variables or defaults
SOCIAL_MEDIA_SEARCH_DESCRIPTION = os.getenv(
    "TOOL_FIND_DESCRIPTION",
    os.getenv(
        "SOCIAL_MEDIA_SEARCH_DESCRIPTION",
        """Search for relevant social media posts based on natural language descriptions. 
The 'query' parameter should describe what you're looking for, and the tool will return the most relevant social media posts. 
Use this when you need to find existing social media posts for reference or to identify similar content."""
    )
)

SOCIAL_MEDIA_STORE_DESCRIPTION = os.getenv(
    "TOOL_STORE_DESCRIPTION", 
    os.getenv(
        "SOCIAL_MEDIA_STORE_DESCRIPTION",
        """Store social media posts for later retrieval. 
The 'information' parameter should contain a natural language description of what the social media post is about, 
while the actual social media post content should be included in the 'metadata' parameter. 
Use this whenever you want to store a social media post for future searching."""
    )
)

# Create settings with environment variables
tool_settings = ToolSettings()
tool_settings.tool_find_description = SOCIAL_MEDIA_SEARCH_DESCRIPTION
tool_settings.tool_store_description = SOCIAL_MEDIA_STORE_DESCRIPTION

# Qdrant settings from environment variables
qdrant_settings = QdrantSettings()
qdrant_settings.location = os.getenv("QDRANT_URL")
qdrant_settings.api_key = os.getenv("QDRANT_API_KEY") 
qdrant_settings.collection_name = os.getenv("COLLECTION_NAME", "social_media")
qdrant_settings.search_limit = int(os.getenv("QDRANT_SEARCH_LIMIT", "10"))
qdrant_settings.read_only = os.getenv("QDRANT_READ_ONLY", "false").lower() == "true"

# Embedding model from environment variable or default
embedding_model_name = os.getenv(
    "EMBEDDING_MODEL", 
    "intfloat/multilingual-e5-large-instruct"
)

logger.info(f"Qdrant settings: URL={qdrant_settings.location}, Collection={qdrant_settings.collection_name}")
logger.info(f"Embedding model: {embedding_model_name}")
logger.info(f"Search limit: {qdrant_settings.search_limit}, Read only: {qdrant_settings.read_only}")

# Create custom embedding provider that returns 'text_dense' as vector name
embedding_provider = CustomFastEmbedProvider(embedding_model_name)

# Create MCP server
logger.info("Creating MCP server...")
mcp = QdrantMCPServer(
    tool_settings=tool_settings,
    qdrant_settings=qdrant_settings,
    embedding_provider=embedding_provider,
)

logger.info("MCP server created successfully!")

# Start the server
if __name__ == "__main__":
    # Use FASTMCP_* variables if available, fall back to HOST/PORT
    host = os.getenv("FASTMCP_HOST") or os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("FASTMCP_PORT") or os.getenv("PORT", "8080"))
    logger.info(f"Starting MCP server with SSE transport on {host}:{port}...")
    mcp.run(transport="sse", host=host, port=port)
