.PHONY: test lint migrate install

install:
	pip install -e .

test:
	pytest tests/

lint:
	flake8 .
	black --check .
	isort --check-only .

migrate:
	alembic upgrade head

dev:
	uvicorn api.main:app --reload 