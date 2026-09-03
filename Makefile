format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run pyright

test:
	uv run pytest

quality: format-check lint typecheck test

format-check:
	uv run ruff format --check .

run:
	uv run lbr-dashboard
