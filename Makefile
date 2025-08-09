# MCP Server Local Testing Makefile

.PHONY: help setup test-env build up down logs test-init test-embedding test-qdrant test-all clean

# Default target
help:
	@echo "MCP Server Local Testing Commands:"
	@echo "  setup         - Set up testing environment"
	@echo "  build         - Build Docker image"
	@echo "  up            - Start MCP server with Docker Compose"
	@echo "  down          - Stop MCP server"
	@echo "  logs          - Show server logs"
	@echo "  test-init     - Test server initialization"
	@echo "  test-embedding - Test embedding model functionality"
	@echo "  test-qdrant   - Test Qdrant connection"
	@echo "  test-integration - Run comprehensive integration test"
	@echo "  test-all      - Run all tests"
	@echo "  clean         - Clean up testing artifacts"

# Setup testing environment
setup:
	@echo "Setting up testing environment..."
	@mkdir -p model_cache logs tests client_scripts
	@echo "Created directories: model_cache, logs, tests, client_scripts"
	@echo "Please update .env.local file with your Qdrant API key"
	@echo "Replace YOUR_QDRANT_API_KEY in .env.local with your actual API key"

# Build Docker image
build:
	@echo "Building MCP server Docker image..."
	docker compose -f docker-compose.test.yml build

# Start services
up:
	@echo "Starting MCP server..."
	docker compose -f docker-compose.test.yml up -d
	@echo "Server starting... Check logs with 'make logs'"
	@echo "Wait a few moments for the server to initialize before running tests"

# Stop services
down:
	@echo "Stopping MCP server..."
	docker compose -f docker-compose.test.yml down

# Show logs
logs:
	docker compose -f docker-compose.test.yml logs -f mcp-server-test

# Test server initialization
test-init:
	@echo "Testing server initialization..."
	docker compose -f docker-compose.test.yml exec -T mcp-client-test python -c "\
import subprocess; \
import sys; \
subprocess.run([sys.executable, '-m', 'pip', 'install', 'aiohttp', 'requests'], check=True); \
exec(open('/app/tests/test_initialization.py').read())"

# Test embedding model
test-embedding:
	@echo "Testing embedding model functionality..."
	docker compose -f docker-compose.test.yml exec -T mcp-client-test python -c "\
import subprocess; \
import sys; \
subprocess.run([sys.executable, '-m', 'pip', 'install', 'aiohttp', 'requests'], check=True); \
exec(open('/app/tests/test_embedding_model.py').read())"

# Test Qdrant connection (run locally, not in container)
test-qdrant:
	@echo "Testing Qdrant connection..."
	@if [ ! -f .env.local ]; then echo "Error: .env.local file not found"; exit 1; fi
	@set -a; source .env.local; set +a; \
	if command -v python3 >/dev/null; then \
		python3 -m pip install --quiet qdrant-client && \
		python3 tests/test_qdrant_connection.py; \
	else \
		echo "Error: python3 not found. Please install Python 3."; \
		exit 1; \
	fi

# Test comprehensive integration
test-integration:
	@echo "Running comprehensive integration test..."
	docker compose -f docker-compose.test.yml exec -T mcp-client-test python -c "\
import subprocess; \
import sys; \
subprocess.run([sys.executable, '-m', 'pip', 'install', 'aiohttp', 'requests'], check=True); \
exec(open('/app/tests/test_integration_full.py').read())"

# Run all tests
test-all: test-qdrant
	@echo "Running all MCP server tests..."
	@echo "Waiting for server to be ready..."
	@sleep 10
	@make test-init
	@echo ""
	@make test-embedding
	@echo ""
	@make test-integration
	@echo ""
	@echo "All tests completed!"

# Clean up
clean:
	@echo "Cleaning up testing artifacts..."
	docker compose -f docker-compose.test.yml down -v
	docker system prune -f
	@echo "Cleaned up logs and model cache (keeping directories)"

# Quick restart
restart: down up
	@echo "Server restarted"

# Status check
status:
	@echo "=== Docker Compose Status ==="
	docker compose -f docker-compose.test.yml ps
	@echo ""
	@echo "=== Server Health Check ==="
	@curl -s http://localhost:8080/health || echo "Server not responding"
