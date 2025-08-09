FROM python:3.11-slim

WORKDIR /app

# Install uv for package management
RUN pip install --no-cache-dir uv

# Copy the entire project to get access to custom_server.py and src
COPY . /app

# Install the mcp-server-qdrant package and dependencies
RUN uv pip install --system --no-cache-dir mcp-server-qdrant fastembed qdrant-client

# Create the model cache directory
RUN mkdir -p /mnt/mcp_model

# Expose the default port for SSE transport (using 8080 to match custom_server.py)
EXPOSE 8080

# Set environment variables with defaults that can be overridden at runtime
ENV QDRANT_URL=""
ENV QDRANT_API_KEY=""
ENV COLLECTION_NAME="default-collection"

# Run the simple server instead of the complex custom one
CMD ["python", "simple_server.py"]
