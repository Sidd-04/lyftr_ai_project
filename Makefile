.PHONY: up down build test test-backend logs clean

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

test:
	docker compose run --rm backend pytest backend/tests/test_api.py -v

test-backend:
	cd backend && PYTHONPATH=. pytest tests/test_api.py -v

logs:
	docker compose logs -f

clean:
	docker compose down -v
