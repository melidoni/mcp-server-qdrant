# Model Caching in Cloud Run

This document explains how model caching works in Cloud Run deployments and how to verify it's functioning correctly.

## 🧠 **Understanding Model Caching**

### **FastEmbed Caching Mechanism**

FastEmbed follows this caching pattern:
1. **First Run**: Downloads model from HuggingFace → Saves to `MODEL_CACHE_DIR`
2. **Subsequent Runs**: Checks `MODEL_CACHE_DIR` → Uses cached model if complete
3. **Cache Miss**: Downloads model again if cache is incomplete or corrupted

### **Cloud Run + GCS Integration**

```yaml
# Cloud Run Configuration
volumeMounts:
- name: mcp_model
  mountPath: /mnt/mcp_model  # MODEL_CACHE_DIR

volumes:
- name: mcp_model
  csi:
    driver: gcsfuse.run.googleapis.com
    volumeAttributes:
      bucketName: zefr-policy-agent-mcp-model-stage
```

**Flow:**
1. **Container Starts** → GCS bucket mounts to `/mnt/mcp_model`
2. **FastEmbed Initializes** → Checks `/mnt/mcp_model` for cached model
3. **Cache Hit** → Uses existing model files (fast startup)
4. **Cache Miss** → Downloads from HuggingFace + saves to GCS (slow startup)

## 📊 **Analyzing Your Current Logs**

### **What's Working ✅**
```
GCSFuse is mounted with bucket zefr-policy-agent-mcp-model-stage
File system has been successfully mounted.
```
- GCS bucket mounting is successful
- `/mnt/mcp_model` is properly connected to GCS

### **Why Model Downloads Occur 🔄**

**Scenario 1: First-Time Cache Population**
- This is the **expected behavior** on first deployment
- Model downloads once and saves to GCS for future use
- Next container restart will use cached version

**Scenario 2: Incomplete Cache**
- Previous download was interrupted
- Missing required files (`refs/main`, ONNX files, etc.)
- FastEmbed treats as cache miss

**Scenario 3: Model Name Mismatch**
- Cached under different directory name
- FastEmbed can't find expected model structure

## 🔍 **Diagnostic Logging (Enhanced)**

With our enhanced logging, you'll now see detailed cache analysis:

```
INFO:custom_fastembed:🔍 Cache directory: /mnt/mcp_model
INFO:custom_fastembed:🔍 Cache exists: True
INFO:custom_fastembed:🎯 Model cache path: /mnt/mcp_model/models--intfloat--multilingual-e5-large-instruct  
INFO:custom_fastembed:🎯 Model cache exists: True
INFO:custom_fastembed:   ✅ refs/main exists: True
INFO:custom_fastembed:   📁 snapshots dir exists: True
INFO:custom_fastembed:   📊 Found 1 snapshots
INFO:custom_fastembed:      📄 Snapshot abc123: 2 ONNX files
```

## 🎯 **Expected Behavior Timeline**

### **First Deployment (Cache Population)**
```
1. Container starts → GCS mounts
2. FastEmbed checks cache → Empty/incomplete
3. Downloads model from HuggingFace
4. Saves to /mnt/mcp_model → Syncs to GCS
5. Model ready for use
```
**Time**: 2-3 minutes (normal)

### **Subsequent Deployments (Cache Hit)**
```
1. Container starts → GCS mounts  
2. FastEmbed checks cache → Complete model found
3. Uses cached model immediately
4. Model ready for use
```
**Time**: 10-20 seconds (fast)

## 🚀 **Verifying Cache Effectiveness**

### **Method 1: Compare Startup Times**
- **First run**: 2-3+ minutes (downloading)
- **Later runs**: 10-30 seconds (using cache)

### **Method 2: Check Logs for Download Activity**
**Cache Miss (downloading):**
```
DEBUG:urllib3.connectionpool:https://huggingface.co:443 "GET /api/models/..."
Falling back to staged write for 'models--intfloat--multilingual-e5-large-instruct/refs/main'
```

**Cache Hit (no downloads):**
```
INFO:custom_fastembed:🎯 Model cache exists: True
INFO:custom_fastembed:Successfully using cached model
```

### **Method 3: Use Diagnostic Script**

Deploy with temporary diagnostic command:
```yaml
# Temporary deployment for cache checking
command: ["python3", "/app/diagnostics/cache_check.py"]
```

## 📈 **Performance Expectations**

| Scenario | Startup Time | HuggingFace Calls | GCS Activity |
|----------|-------------|-------------------|--------------|
| **First Run** | 2-3 minutes | ✅ Model download | ✅ Write to bucket |
| **Cache Hit** | 10-30 seconds | ❌ None | ✅ Read from bucket |  
| **Cache Miss** | 2-3 minutes | ✅ Re-download | ✅ Overwrite bucket |

## 🛠️ **Troubleshooting Cache Issues**

### **Problem: Model Always Downloads**

**Check 1: Verify Model Directory Name**
```bash
# Expected structure in GCS bucket:
/models--intfloat--multilingual-e5-large-instruct/
├── refs/main
├── snapshots/
│   └── [hash]/
│       ├── onnx/model.onnx
│       └── onnx/model.onnx_data
```

**Check 2: Verify File Completeness**
```bash
# Required files for cache hit:
- refs/main (contains snapshot hash)
- snapshots/[hash]/onnx/model.onnx
- snapshots/[hash]/onnx/model.onnx_data  
```

**Check 3: Check Permissions**
```bash
# Service account needs:
- storage.objects.get (read cache)
- storage.objects.create (write cache)
- storage.objects.update (update cache)
```

### **Problem: Partial Cache Corruption**

**Solution: Clear and Rebuild Cache**
```bash
# Option 1: Clear GCS bucket contents
gsutil -m rm -r gs://zefr-policy-agent-mcp-model-stage/*

# Option 2: Force re-download by changing model name temporarily
EMBEDDING_MODEL=multilingual-e5-large-instruct-v2  # Forces new download
```

## 📋 **Best Practices**

### **1. Monitor Cache Effectiveness**
- Track startup times in Cloud Run logs
- Set up alerts for unusual download activity
- Monitor GCS bucket growth

### **2. Cache Warmup Strategy**  
```bash
# Pre-populate cache in CI/CD
docker run --rm \
  -v cache-volume:/mnt/mcp_model \
  -e MODEL_CACHE_DIR=/mnt/mcp_model \
  your-image python3 -c "
from mcp_server_qdrant.embeddings.custom_fastembed import CustomFastEmbedProvider
provider = CustomFastEmbedProvider('multilingual-e5-large-instruct', 'intfloat/multilingual-e5-large-instruct')
print('Model cached successfully')
"
```

### **3. Cache Validation**
- Include diagnostic logging in production deployments
- Implement health checks that verify model loading time
- Set up monitoring for cache hit rates

## 🎯 **Current Status Analysis**

Based on your logs, **this appears to be normal first-run behavior**:

1. ✅ **GCS mounting works correctly**
2. 🔄 **Model downloading (expected for first run)**  
3. 📁 **Files being written to cache** (`staged write`)
4. ⏱️ **Next restart should use cached model**

**Expected Result**: The next deployment should show dramatically faster startup with no HuggingFace downloads.

## 🔧 **Immediate Action Items**

1. **Monitor next deployment** for faster startup times
2. **Check enhanced logs** for cache status details  
3. **Run diagnostic script** if cache issues persist
4. **Verify GCS bucket contents** after successful startup

---

**Key Takeaway**: The model download you're seeing is likely the **one-time cache population**. Subsequent deployments should be much faster once the cache is established.
