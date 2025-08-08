# Custom Changes Made to qdrant-mcp-server

This document outlines the custom modifications made to the qdrant-mcp-server project.

## Files Added/Modified:

### 1. custom_server.py (NEW FILE)
- **Purpose**: Custom MCP server implementation with specialized embedding provider
- **Key Features**:
  - Custom FastEmbed provider supporting HuggingFace models
  - Specialized query prefix for social media captions
  - Uses multilingual-e5-large-instruct model (1024 dimensions)
  - SSE transport on port 8080

### Key Custom Configuration:
- **Model**: `multilingual-e5-large-instruct` from HuggingFace (`intfloat/multilingual-e5-large-instruct`)
- **Vector Dimension**: 1024
- **Cache Directory**: `/mnt/mcp_model`
- **Query Prefix**: "Instruct: Given a query of a social media caption, find other social media captions that are most relevant. Query: "
- **Vector Name**: `text_dense` (for collection compatibility)
- **Transport**: SSE on host 0.0.0.0, port 8080

### Implementation Details:
- Extends `EmbeddingProvider` base class
- Implements `embed_documents()` and `embed_query()` methods
- Registers custom model with FastEmbed during initialization
- Uses asyncio for non-blocking embedding operations

## Original Repository:
- Source: https://github.com/qdrant/mcp-for-docs
- File referenced: qdrant_docs_mcp/server.py

## Next Steps:
1. Convert to Git submodule pointing to original Qdrant repository
2. Re-apply custom_server.py to the submodule
3. Ensure all custom configurations are preserved
