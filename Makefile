COMPOSE = docker compose

.PHONY: up down logs fmt lint typecheck tests build poetry

poetry:
	poetry install

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

fmt:
	poetry run black .

lint:
	poetry run ruff check .

typecheck:
	poetry run mypy .

tests:
	poetry run pytest

build:
	@echo "no build configured"
