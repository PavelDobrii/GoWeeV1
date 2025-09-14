COMPOSE = docker compose

.PHONY: up down logs fmt lint tests build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

fmt:
	@echo "no formatting configured"

lint:
	@echo "no lint configured"

tests:
	@echo "no tests configured"

build:
	@echo "no build configured"
