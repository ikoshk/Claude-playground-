# IT Maturity Assessment – Makefile
.PHONY: help up down build dev worker demo clean logs

PYTHON ?= python3
DC = docker compose

help:
	@echo ""
	@echo "  IT Maturity Assessment MVP"
	@echo "  ─────────────────────────────────────────────────────────"
	@echo "  make demo      – Start in demo mode (no API keys needed)"
	@echo "  make up        – Start all services (requires .env)"
	@echo "  make down      – Stop all services"
	@echo "  make build     – Rebuild Docker images"
	@echo "  make dev       – Run FastAPI locally (no Docker)"
	@echo "  make worker    – Run Celery worker locally (no Docker)"
	@echo "  make logs      – Tail API logs"
	@echo "  make clean     – Remove volumes and containers"
	@echo ""

## Start in demo mode (stub search + demo LLM, no API keys needed)
demo:
	@echo "Starting in DEMO mode (stub search + demo LLM)..."
	SEARCH_PROVIDER=stub LLM_MODE=demo $(DC) up --build

## Start all services (reads .env)
up:
	$(DC) up --build

## Stop services
down:
	$(DC) down

## Rebuild images
build:
	$(DC) build

## Run FastAPI locally (development, no Docker)
dev:
	@if [ ! -f .env ]; then cp .env.example .env; fi
	ARTIFACTS_DIR=./artifacts $(PYTHON) -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

## Run Celery worker locally
worker:
	@if [ ! -f .env ]; then cp .env.example .env; fi
	ARTIFACTS_DIR=./artifacts celery -A backend.tasks.celery_app worker --loglevel=info --queues=assessments --concurrency=2

## Tail API service logs
logs:
	$(DC) logs -f api

## Remove all containers and volumes (destructive)
clean:
	$(DC) down -v --remove-orphans
	rm -rf ./artifacts

## Run a quick smoke test (requires running services)
smoke-test:
	@echo "Running smoke test..."
	curl -s http://localhost:8000/health | python3 -m json.tool
	curl -s -X POST http://localhost:8000/api/assessments \
	  -H "Content-Type: application/json" \
	  -d '{"company_name": "Accenture", "company_domain": "accenture.com"}' \
	  | python3 -m json.tool
