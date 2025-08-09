import os
import logging
from custom_server import main

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting MCP server with official Qdrant structure...")
    main()
