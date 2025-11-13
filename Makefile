.PHONY: help install dev-install test lint format clean docker-build docker-up docker-down run init-db stats

help:
	@echo "Nostr Data Pipeline - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install production dependencies"
	@echo "  make dev-install   Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linters (ruff, mypy)"
	@echo "  make format       Format code with black"
	@echo "  make clean        Clean build artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-up    Start all services"
	@echo "  make docker-down  Stop all services"
	@echo "  make docker-logs  View logs"
	@echo ""
	@echo "Pipeline:"
	@echo "  make init-db      Initialize database"
	@echo "  make run          Run the pipeline"
	@echo "  make stats        Show network statistics"
	@echo "  make trending     Show trending hashtags"

install:
	pip install -r requirements.txt
	pip install -e .

dev-install:
	pip install -r requirements.txt
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=nostr_pipeline --cov-report=html

lint:
	ruff check src/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	docker-compose logs -f pipeline

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

init-db:
	nostr-pipeline init-db

run:
	nostr-pipeline run

stats:
	nostr-pipeline stats

trending:
	nostr-pipeline trending --hours 24 --limit 20
