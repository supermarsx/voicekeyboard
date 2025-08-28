.PHONY: help install dev lint fmt type test docs docs-serve pre-commit

help:
	@echo "Targets: install dev lint fmt type test docs docs-serve pre-commit"

install:
	python -m pip install -U pip
	python -m pip install .

dev:
	python -m pip install -U pip
	python -m pip install -e .[dev]

lint:
	python -m ruff check .

fmt:
	python -m ruff check --fix .
	python -m black .

type:
	python -m mypy --hide-error-codes --pretty voicekeyboard

test:
	python -m pytest -q

docs:
	python -m mkdocs build --strict

docs-serve:
	python -m mkdocs serve -a 0.0.0.0:8000

pre-commit:
	pre-commit install
	pre-commit run --all-files

