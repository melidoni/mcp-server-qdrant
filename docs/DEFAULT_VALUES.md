# Environment Variable Default Values

This document lists the exact default values used when environment variables are not provided.

## 📊 **Complete Default Values Reference**

### **🔗 Qdrant Connection Settings**

| Environment Variable | Default Value | Source |
|---------------------|---------------|--------|
| `QDRANT_URL` | `None` | [`settings.py:79`](../src/mcp_server_qdrant/settings.py#L79) |
| `QDRANT_API_KEY` | `None` | [`settings.py:80`](../src/mcp_server_qdrant/settings.py#L80) |
| `COLLECTION_NAME` | `None` | [`settings.py:81-83`](../src/mcp_server_qdrant/settings.py#L81-83) |
| `QDRANT_LOCAL_PATH` | `None` | [`settings.py:84`](../src/mcp_server_qdrant/settings.py#L84) |
| `QDRANT_SEARCH_LIMIT` | `10` | [`settings.py:85`](../src/mcp_server_qdrant/settings.py#L85) |
| `QDRANT_READ_ONLY` | `false` | [`settings.py:86`](../src/mcp_server_qdrant/settings.py#L86) |
| `QDRANT_ALLOW_ARBITRARY_FILTER` | `false` | [`settings.py:90-92`](../src/mcp_server_qdrant/settings.py#L90-92) |

### **🤖 Embedding Provider Settings**

| Environment Variable | Default Value | Source |
|---------------------|---------------|--------|
| `EMBEDDING_PROVIDER` | `"fastembed"` | [`settings.py:41-43`](../src/mcp_server_qdrant/settings.py#L41-43) |
| `EMBEDDING_MODEL` | `"sentence-transformers/all-MiniLM-L6-v2"` | [`settings.py:45-48`](../src/mcp_server_qdrant/settings.py#L45-48) |
| `CUSTOM_HF_MODEL_ID` | `None` | [`factory.py:22`](../src/mcp_server_qdrant/embeddings/factory.py#L22) |
| `CUSTOM_QUERY_PREFIX` | `None` (Optional - has built-in fallback) | [`factory.py:24`](../src/mcp_server_qdrant/embeddings/factory.py#L24) |
| `MODEL_CACHE_DIR` | `"/mnt/mcp_model"` | [`factory.py:23`](../src/mcp_server_qdrant/embeddings/factory.py#L23) |

### **🛠️ Tool Descriptions**

| Environment Variable | Default Value | Source |
|---------------------|---------------|--------|
| `TOOL_STORE_DESCRIPTION` | `"Keep the memory for later use, when you are asked to remember something."` | [`settings.py:8-10`](../src/mcp_server_qdrant/settings.py#L8-10) → [`settings.py:26-29`](../src/mcp_server_qdrant/settings.py#L26-29) |
| `TOOL_FIND_DESCRIPTION` | `"Look up memories in Qdrant. Use this tool when you need to: \n - Find memories by their content \n - Access memories for further analysis \n - Get some personal information about the user"` | [`settings.py:11-16`](../src/mcp_server_qdrant/settings.py#L11-16) → [`settings.py:30-33`](../src/mcp_server_qdrant/settings.py#L30-33) |

### **🚀 Server & Performance Settings**

| Environment Variable | Default Value | Source |
|---------------------|---------------|--------|
| `FASTMCP_HOST` | `"127.0.0.1"` | FastMCP framework default |
| `FASTMCP_PORT` | `"8000"` | FastMCP framework default |
| `FASTMCP_LOG_LEVEL` | `"INFO"` | FastMCP framework default |
| `LOG_LEVEL` | Not set | Standard Python logging |
| `PYTHONUNBUFFERED` | Not set | Standard Python behavior |

## 🎯 **Behavior with Default Values**

### **Default Configuration (No Environment Variables)**
```bash
# This is what runs if you provide NO environment variables:
EMBEDDING_PROVIDER="fastembed"
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
QDRANT_SEARCH_LIMIT=10
QDRANT_READ_ONLY=false
MODEL_CACHE_DIR="/mnt/mcp_model"
FASTMCP_HOST="127.0.0.1"
FASTMCP_PORT="8000"
TOOL_STORE_DESCRIPTION="Keep the memory for later use, when you are asked to remember something."
TOOL_FIND_DESCRIPTION="Look up memories in Qdrant. Use this tool when you need to: ..."
```

### **Required Variables (Will Cause Startup Failure)**
```bash
# These MUST be provided or the server will fail:
QDRANT_URL=None          # ❌ Required for remote Qdrant
QDRANT_API_KEY=None      # ❌ Required for cloud Qdrant  
COLLECTION_NAME=None     # ❌ Required to specify collection
```

### **Custom Provider Fallback Behavior**
```bash
# When EMBEDDING_PROVIDER="custom_fastembed":
CUSTOM_HF_MODEL_ID=None           # Optional - Uses EMBEDDING_MODEL value instead
CUSTOM_QUERY_PREFIX=None          # Optional - Falls back to built-in social media prefix
MODEL_CACHE_DIR="/mnt/mcp_model"  # Uses default cache location
```

## ⚠️ **Important Notes**

### **1. Required vs Optional Variables**
- **REQUIRED**: `QDRANT_URL`, `QDRANT_API_KEY`, `COLLECTION_NAME`
- **OPTIONAL**: All others have sensible defaults

### **2. Custom Provider Behavior**
When `EMBEDDING_PROVIDER="custom_fastembed"`:
- `CUSTOM_QUERY_PREFIX` is **optional** - automatically falls back to built-in social media instruction prefix
- `CUSTOM_HF_MODEL_ID` is **optional** - uses the `EMBEDDING_MODEL` value instead

### **3. Local vs Remote Mode**
- **Remote**: Requires `QDRANT_URL` + `QDRANT_API_KEY`
- **Local**: Requires `QDRANT_LOCAL_PATH` (conflicts with URL/API_KEY)

### **4. Tool Description Defaults**
The default tool descriptions are generic "memory" focused. For specialized use cases (social media, code search), you should override these.

## 📋 **Production Recommendations**

### **Always Specify These:**
```bash
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_api_key  
COLLECTION_NAME=your_collection
FASTMCP_HOST=0.0.0.0  # For container deployment
FASTMCP_PORT=8080     # Standard container port
```

### **Override for Specialized Use Cases:**
```bash
# Social Media Focused
EMBEDDING_PROVIDER=custom_fastembed
CUSTOM_QUERY_PREFIX="Your social media instruction prefix"
TOOL_STORE_DESCRIPTION="Store social media posts..."
TOOL_FIND_DESCRIPTION="Search for social media posts..."

# Code Search Focused  
TOOL_STORE_DESCRIPTION="Store code snippets..."
TOOL_FIND_DESCRIPTION="Search for code snippets..."
```

---

**Key Takeaway**: Most variables have sensible defaults, but connection details (`QDRANT_URL`, `QDRANT_API_KEY`, `COLLECTION_NAME`) are required and must be provided.
