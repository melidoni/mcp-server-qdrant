# Runtime Configuration Guide

This guide covers all runtime configuration options for the MCP Server, allowing you to customize behavior without rebuilding the container.

> [!NOTE]
> For exact default values when environment variables are not provided, see **[`docs/DEFAULT_VALUES.md`](DEFAULT_VALUES.md)**

## 🔧 **Core Concept: Zero Build-Time Dependencies**

All configuration is handled via **environment variables at runtime**. The same Docker image can be deployed to multiple environments with different configurations.

## 📋 **Complete Configuration Reference**

### **🔗 Qdrant Connection Settings**

| Environment Variable | Description | Default | Required |
|---------------------|-------------|---------|----------|
| `QDRANT_URL` | Qdrant server URL | `None` | Yes (unless `QDRANT_LOCAL_PATH`) |
| `QDRANT_API_KEY` | Qdrant API key for authentication | `None` | Yes (for cloud instances) |
| `COLLECTION_NAME` | Collection name to use | `None` | Yes |
| `QDRANT_LOCAL_PATH` | Local Qdrant database path | `None` | Alternative to `QDRANT_URL` |
| `QDRANT_SEARCH_LIMIT` | Maximum search results | `10` | No |
| `QDRANT_READ_ONLY` | Read-only mode | `false` | No |

**Examples:**
```bash
# Cloud Qdrant
QDRANT_URL=https://your-instance.us-east.aws.cloud.qdrant.io
QDRANT_API_KEY=your_api_key_here
COLLECTION_NAME=social_media

# Local Qdrant
QDRANT_LOCAL_PATH=/path/to/local/qdrant
COLLECTION_NAME=local_collection
```

### **🤖 Embedding Provider Settings**

| Environment Variable | Description | Default | Required |
|---------------------|-------------|---------|----------|
| `EMBEDDING_PROVIDER` | Provider type (`fastembed` or `custom_fastembed`) | `fastembed` | No |
| `EMBEDDING_MODEL` | Model name to use | `sentence-transformers/all-MiniLM-L6-v2` | No |
| `CUSTOM_HF_MODEL_ID` | HuggingFace model ID for custom provider | `None` | Required for `custom_fastembed` |
| `CUSTOM_QUERY_PREFIX` | Query prefix for search optimization | Built-in social media prefix | No |
| `MODEL_CACHE_DIR` | Directory for model caching | `/mnt/mcp_model` | No |

**Examples:**
```bash
# Standard FastEmbed
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Custom social media optimized
EMBEDDING_PROVIDER=custom_fastembed
EMBEDDING_MODEL=multilingual-e5-large-instruct
CUSTOM_HF_MODEL_ID=intfloat/multilingual-e5-large-instruct
CUSTOM_QUERY_PREFIX="Instruct: Given a query of a social media caption, find other social media captions that are most relevant. Query: "
MODEL_CACHE_DIR=/mnt/mcp_model
```

### **🛠️ Tool Descriptions (User-Facing)**

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `TOOL_STORE_DESCRIPTION` | Description shown to users for the store tool | Generic memory storage |
| `TOOL_FIND_DESCRIPTION` | Description shown to users for the find tool | Generic memory retrieval |

**Examples:**
```bash
# Social Media Focused
TOOL_STORE_DESCRIPTION="Store social media posts for later retrieval. The information parameter should contain a natural language description of what the social media post is about, while the actual social media post content should be included in the metadata parameter as a caption property."

TOOL_FIND_DESCRIPTION="Search for relevant social media posts based on natural language descriptions. The query parameter should describe what you are looking for, and the tool will return the most relevant social media posts."

# Code Search Focused  
TOOL_STORE_DESCRIPTION="Store reusable code snippets for later retrieval. The information parameter should contain a natural language description of what the code does, while the actual code should be included in the metadata parameter as a code property."

TOOL_FIND_DESCRIPTION="Search for relevant code snippets based on natural language descriptions. The query parameter should describe the functionality you are looking for."
```

### **🚀 Server & Performance Settings**

| Environment Variable | Description | Default | Required |
|---------------------|-------------|---------|----------|
| `FASTMCP_HOST` | Host to bind the server | `127.0.0.1` | No |
| `FASTMCP_PORT` | Port to run the server | `8000` | No |
| `FASTMCP_LOG_LEVEL` | Logging level | `INFO` | No |
| `LOG_LEVEL` | Application log level | `INFO` | No |
| `PYTHONUNBUFFERED` | Python output buffering | Not set | No |

**Examples:**
```bash
# Production settings
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8080
FASTMCP_LOG_LEVEL=WARNING

# Development settings  
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=8000
FASTMCP_LOG_LEVEL=DEBUG
LOG_LEVEL=DEBUG
PYTHONUNBUFFERED=1
```

## 📁 **Configuration Templates**

### **Using .env.template**

Copy the provided template:
```bash
cp .env.template .env.local
# Edit .env.local with your values
```

Reference: **[`.env.template`](../.env.template)** | Default Values: **[`DEFAULT_VALUES.md`](DEFAULT_VALUES.md)**

### **Docker Compose Configuration**

```yaml
# docker-compose.yml
version: '3.8'
services:
  mcp-server:
    image: your-mcp-server:latest
    ports:
      - "8080:8080"
    environment:
      FASTMCP_HOST: 0.0.0.0
      QDRANT_URL: ${QDRANT_URL}
      QDRANT_API_KEY: ${QDRANT_API_KEY}
      COLLECTION_NAME: ${COLLECTION_NAME}
      EMBEDDING_PROVIDER: custom_fastembed
```

### **Kubernetes Configuration**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
spec:
  template:
    spec:
      containers:
      - name: mcp-server
        image: your-mcp-server:latest
        env:
        - name: QDRANT_URL
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: qdrant-url
        - name: QDRANT_API_KEY
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: qdrant-api-key
        - name: COLLECTION_NAME
          value: "production_data"
```

### **Cloud Run Configuration**

```yaml
# cloud-run-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    spec:
      containers:
      - image: gcr.io/your-project/mcp-server:latest
        env:
        - name: FASTMCP_HOST
          value: "0.0.0.0"
        - name: FASTMCP_PORT  
          value: "8080"
        - name: QDRANT_URL
          valueFrom:
            secretKeyRef:
              name: qdrant-config
              key: url
        - name: QDRANT_API_KEY
          valueFrom:
            secretKeyRef:
              name: qdrant-config
              key: api-key
```

## 🔄 **Environment-Specific Configurations**

### **Development**
```bash
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=8000
FASTMCP_LOG_LEVEL=DEBUG
QDRANT_LOCAL_PATH=/tmp/qdrant_dev
COLLECTION_NAME=dev_test
EMBEDDING_PROVIDER=fastembed
```

### **Staging**
```bash
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8080
QDRANT_URL=https://staging-qdrant.example.com
QDRANT_API_KEY=staging_api_key
COLLECTION_NAME=staging_data
EMBEDDING_PROVIDER=custom_fastembed
```

### **Production**
```bash
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8080
FASTMCP_LOG_LEVEL=WARNING
QDRANT_URL=https://prod-qdrant.example.com
QDRANT_API_KEY=prod_api_key
COLLECTION_NAME=production_data
EMBEDDING_PROVIDER=custom_fastembed
CUSTOM_HF_MODEL_ID=intfloat/multilingual-e5-large-instruct
```

## 🔐 **Security Best Practices**

1. **Never hardcode secrets** - Always use environment variables
2. **Use secret management** - Kubernetes secrets, Cloud secret managers
3. **Separate configs per environment** - Different .env files per stage
4. **Validate required variables** - The server will fail fast if required vars are missing
5. **Use read-only mode** - Set `QDRANT_READ_ONLY=true` for read-only deployments

## 🧪 **Testing Configuration**

```bash
# Test with different configurations
docker run --rm \
  -e QDRANT_URL=http://localhost:6333 \
  -e COLLECTION_NAME=test_collection \
  -e EMBEDDING_PROVIDER=fastembed \
  -e FASTMCP_LOG_LEVEL=DEBUG \
  your-mcp-server:latest

# Test with custom embedding
docker run --rm \
  -e QDRANT_URL=your_test_instance \
  -e QDRANT_API_KEY=test_key \
  -e COLLECTION_NAME=test_social_media \
  -e EMBEDDING_PROVIDER=custom_fastembed \
  -e CUSTOM_HF_MODEL_ID=intfloat/multilingual-e5-large-instruct \
  your-mcp-server:latest
```

## 📊 **Configuration Validation**

The server validates configuration on startup and will exit with clear error messages if:

- Required variables are missing
- Invalid provider types are specified  
- Conflicting settings are detected (e.g., both `QDRANT_URL` and `QDRANT_LOCAL_PATH`)

**Example error messages:**
```
ValueError: QDRANT_URL or QDRANT_LOCAL_PATH must be provided
ValueError: QDRANT_API_KEY is required when using remote Qdrant instance
ValueError: If 'local_path' is set, 'location' and 'api_key' must be None
```

## 🎯 **Use Case Examples**

### **Social Media Analysis**
```bash
EMBEDDING_PROVIDER=custom_fastembed
CUSTOM_QUERY_PREFIX="Instruct: Given a query of a social media caption, find other social media captions that are most relevant. Query: "
TOOL_STORE_DESCRIPTION="Store social media posts for later retrieval..."
TOOL_FIND_DESCRIPTION="Search for relevant social media posts..."
```

### **Code Search**
```bash
EMBEDDING_PROVIDER=fastembed  
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
TOOL_STORE_DESCRIPTION="Store reusable code snippets..."
TOOL_FIND_DESCRIPTION="Search for relevant code snippets..."
```

### **General Knowledge Base**
```bash
EMBEDDING_PROVIDER=fastembed
TOOL_STORE_DESCRIPTION="Keep information for later use..."
TOOL_FIND_DESCRIPTION="Look up stored information..."
```

---

**Key Takeaway**: The same Docker image can serve completely different use cases just by changing environment variables!
