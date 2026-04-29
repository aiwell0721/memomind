# MemoMind Makefile
# Common development and deployment tasks

.PHONY: help install test test-mcp test-all lint docker-build docker-up docker-down docker-logs clean

help: ## Show this help message
	@echo "MemoMind - Makefile Commands"
	@echo "============================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

test: ## Run unit tests
	python -m pytest tests/ -v --tb=short

test-mcp: ## Run MCP Server tests only
	python -m pytest tests/test_mcp_server.py -v --tb=short

test-all: test ## Run all tests with coverage
	python -m pytest tests/ -v --cov=core --cov=api --cov=mcp_server --tb=short

lint: ## Run linting
	python -m flake8 core/ api/ mcp_server/ --max-line-length=120

docker-build: ## Build Docker image
	docker compose build

docker-up: ## Start Docker containers
	docker compose up -d
	@echo "MemoMind started at http://localhost:8000"
	@echo "Swagger docs at http://localhost:8000/docs"
	@echo "MCP Server at http://localhost:8001"

docker-down: ## Stop Docker containers
	docker compose down

docker-logs: ## View Docker logs
	docker compose logs -f memomind

docker-shell: ## Open shell in Docker container
	docker compose exec memomind /bin/bash

mcp-stdio: ## Run MCP Server in stdio mode (for Claude Desktop)
	python -m mcp_server --db memomind.db

mcp-http: ## Run MCP Server in HTTP mode
	python -m mcp_server --db memomind.db --transport http --port 8001

api: ## Start REST API server
	python -c "from core.api_server import create_app; import uvicorn; uvicorn.run(create_app('memomind.db'), host='0.0.0.0', port=8000)"

cli-create: ## Create a note via CLI
	python cli.py create --title "$(title)" --content "$(content)"

cli-search: ## Search notes via CLI
	python cli.py search "$(query)"

cli-list: ## List all notes via CLI
	python cli.py list

clean: ## Remove temporary files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache/ .coverage htmlcov/
	rm -rf *.db
