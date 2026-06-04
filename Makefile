.PHONY: install dev build lint typecheck test format format-check api-dev web-dev

install:
	pnpm install
	cd apps/api && uv sync

dev:
	pnpm dev

build:
	pnpm build

lint:
	pnpm lint

typecheck:
	pnpm typecheck

test:
	pnpm test

format:
	pnpm format
	cd apps/api && uv run ruff format .

format-check:
	pnpm format:check
	cd apps/api && uv run ruff format --check .

api-dev:
	cd apps/api && uv run uvicorn app.main:app --reload

web-dev:
	pnpm --filter @ai-vea/web dev
