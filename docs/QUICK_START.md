# MCP Server Local Testing - Quick Start Guide

This guide will help you quickly test your remote MCP server locally using Docker.

## Prerequisites

- Docker and Docker Compose installed
- Your Qdrant API key
- Python 3.11+ (for Qdrant connection tests)

## Step 1: Configure Environment

1. **Update your API key** in [`.env.local`](../.env.local:11):
   ```bash
   # Replace YOUR_QDRANT_API_KEY with your actual API key
   QDRANT_API_KEY=your_actual_api_key_here
   ```

2. **Verify configuration**:
   ```bash
   cat .env.local | grep QDRANT_API_KEY
   ```

💡 **Need more configuration options?** See the complete [Configuration Guide](CONFIGURATION.md) for all runtime settings including custom models, tool descriptions, and deployment options.

## Step 2: Quick Test (Recommended)

Run this single command to test everything:

```bash
make test-qdrant && make build && make up && sleep 30 && make test-integration
```

This will:
- ✅ Test Qdrant connection
- 🏗️ Build the Docker image
- 🚀 Start the MCP server
- ⏳ Wait for initialization
- 🧪 Run comprehensive integration tests

## Step 3: Manual Testing (Alternative)

If you prefer step-by-step testing:

```bash
# 1. Test Qdrant connection first
make test-qdrant

# 2. Build and start server
make build
make up

# 3. Monitor startup logs (in another terminal)
make logs

# 4. Wait for model loading (usually 1-2 minutes)
# Look for: "Successfully registered custom model 'multilingual-e5-large-instruct'"

# 5. Run tests
make test-integration
```

## Expected Results

### ✅ Successful Test Output

```
=== INTEGRATION TEST SUMMARY ===
mcp_init              ✓ PASS
tools_available       ✓ PASS  
store_functionality   ✓ PASS
find_functionality    ✓ PASS
embedding_quality     ✓ PASS
---------------------------------
Total: 5/5 tests passed
🎉 ALL TESTS PASSED! MCP Server is ready for production.
```

### 🔍 Key Log Messages to Look For

In `make logs`, you should see:
```
INFO: Successfully registered custom model 'multilingual-e5-large-instruct'
INFO: Starting MCP server with SSE transport on 0.0.0.0:8080...
INFO: Embedding query with prefix: 'Instruct: Given a query...'
```

## Step 4: Cleanup

```bash
# Stop server
make down

# Clean up resources
make clean
```

## Troubleshooting

### Problem: "Server not responding"
**Solution**: The custom embedding model takes time to download and load (1-2 minutes on first run).

### Problem: "Qdrant connection failed"
**Solution**: 
1. Check your API key in [`.env.local`](../.env.local:11)
2. Verify network connectivity: `curl -H "api-key: YOUR_API_KEY" https://0e76560f-4158-4cac-b41e-eb9830d1755f.us-east4-0.gcp.cloud.qdrant.io`

### Problem: "Model registration failed"
**Solution**: 
1. Check available disk space (model needs ~2GB)
2. Check [`model_cache/`](../model_cache/) directory permissions

### Problem: "Container build failed"
**Solution**: Check Docker is running and has sufficient resources allocated

## Understanding the Tests

| Test | What it validates |
|------|------------------|
| **Qdrant Connection** | Remote Qdrant access with API key |
| **MCP Initialization** | Protocol handshake and setup |
| **Tools Available** | `find` and `store` tools registered |
| **Store Functionality** | Embedding generation and storage |
| **Find Functionality** | Query processing with custom prefix |
| **Embedding Quality** | Semantic similarity matching |

## Production Readiness Checklist

- [ ] All tests pass locally ✅
- [ ] Model loads within acceptable time ⏱️
- [ ] Query prefix applied correctly 🔍
- [ ] Qdrant operations work reliably 🔗
- [ ] Memory usage is acceptable 💾

## Next Steps

Once local testing passes:

1. **Deploy to Cloud Run**: Your existing CI/CD pipeline will handle deployment
2. **Monitor Performance**: Check model loading time and query response times
3. **Integration Testing**: Test with your policy agent
4. **Production Monitoring**: Set up alerts for health and performance

## Commands Reference

```bash
make help              # Show all available commands
make setup             # Initial setup
make build             # Build Docker image  
make up                # Start server
make logs              # Show server logs
make test-qdrant       # Test Qdrant connection
make test-integration  # Run full integration test
make test-all          # Run all tests
make down              # Stop server
make clean             # Cleanup
make status            # Check server status
```

---

🎯 **Goal**: All tests should pass, indicating your MCP server with custom [`multilingual-e5-large-instruct`](../custom_server.py:94) model is working correctly!
