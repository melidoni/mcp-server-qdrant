#!/usr/bin/env python3
"""
Model Cache Diagnostics Script

This script checks the FastEmbed model cache to understand
why models might be downloading instead of using cached versions.
"""

import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_cache_directory(cache_dir="/mnt/mcp_model"):
    """Check the contents of the model cache directory."""
    cache_path = Path(cache_dir)
    
    logger.info(f"🔍 Checking cache directory: {cache_path}")
    
    if not cache_path.exists():
        logger.warning(f"❌ Cache directory does not exist: {cache_path}")
        return False
        
    if not cache_path.is_dir():
        logger.warning(f"❌ Cache path is not a directory: {cache_path}")
        return False
        
    logger.info(f"✅ Cache directory exists: {cache_path}")
    
    # List all contents recursively
    total_files = 0
    total_size = 0
    model_dirs = []
    
    try:
        for item in cache_path.rglob("*"):
            if item.is_file():
                total_files += 1
                size = item.stat().st_size
                total_size += size
                logger.info(f"📄 File: {item.relative_to(cache_path)} ({size:,} bytes)")
            elif item.is_dir():
                if "models--" in item.name:
                    model_dirs.append(item)
                logger.info(f"📁 Directory: {item.relative_to(cache_path)}")
                
        logger.info(f"📊 Summary: {total_files} files, {total_size:,} bytes total")
        
        # Check for specific model directories
        logger.info(f"🤖 Found {len(model_dirs)} model directories:")
        for model_dir in model_dirs:
            logger.info(f"   📁 {model_dir.name}")
            
            # Check for critical files
            refs_main = model_dir / "refs" / "main"
            if refs_main.exists():
                logger.info(f"   ✅ Has refs/main")
            else:
                logger.warning(f"   ❌ Missing refs/main")
                
            # Look for ONNX files
            onnx_files = list(model_dir.rglob("*.onnx"))
            if onnx_files:
                logger.info(f"   ✅ Has {len(onnx_files)} ONNX files")
                for onnx in onnx_files:
                    logger.info(f"      📄 {onnx.relative_to(model_dir)}")
            else:
                logger.warning(f"   ❌ No ONNX files found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error scanning cache directory: {e}")
        return False

def check_model_specific_cache(model_name="multilingual-e5-large-instruct"):
    """Check cache for specific model."""
    cache_dir = Path(os.getenv("MODEL_CACHE_DIR", "/mnt/mcp_model"))
    
    # FastEmbed uses this naming convention
    model_cache_name = f"models--intfloat--{model_name}"
    model_path = cache_dir / model_cache_name
    
    logger.info(f"🎯 Checking specific model cache: {model_cache_name}")
    
    if model_path.exists():
        logger.info(f"✅ Model directory exists: {model_path}")
        
        # Check for required files
        required_files = [
            "refs/main",
            "snapshots",
        ]
        
        for req_file in required_files:
            file_path = model_path / req_file
            if file_path.exists():
                logger.info(f"   ✅ {req_file} exists")
            else:
                logger.warning(f"   ❌ {req_file} missing")
                
        # Check snapshot directory
        snapshots_dir = model_path / "snapshots"
        if snapshots_dir.exists():
            snapshots = list(snapshots_dir.iterdir())
            logger.info(f"   📁 Found {len(snapshots)} snapshots")
            
            for snapshot in snapshots:
                if snapshot.is_dir():
                    logger.info(f"      📁 Snapshot: {snapshot.name}")
                    
                    # Check for ONNX files in snapshot
                    onnx_files = list(snapshot.rglob("*.onnx*"))
                    if onnx_files:
                        logger.info(f"         ✅ {len(onnx_files)} ONNX files")
                    else:
                        logger.warning(f"         ❌ No ONNX files in snapshot")
        
        return True
    else:
        logger.warning(f"❌ Model directory not found: {model_path}")
        return False

def main():
    """Run cache diagnostics."""
    logger.info("🚀 Starting FastEmbed Cache Diagnostics")
    logger.info("=" * 50)
    
    # Check environment variables
    cache_dir = os.getenv("MODEL_CACHE_DIR", "/mnt/mcp_model")
    logger.info(f"🔧 MODEL_CACHE_DIR: {cache_dir}")
    
    # Check general cache
    logger.info("\n📂 GENERAL CACHE CHECK")
    logger.info("-" * 30)
    check_cache_directory(cache_dir)
    
    # Check specific model
    logger.info("\n🎯 SPECIFIC MODEL CHECK")
    logger.info("-" * 30)
    check_model_specific_cache()
    
    logger.info("\n✅ Cache diagnostics complete!")

if __name__ == "__main__":
    main()
