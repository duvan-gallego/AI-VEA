# AI VEA (AI Video Engagement Analyzer)

A modern monorepo scaffold with a React + TypeScript frontend and a FastAPI backend.

## Stack

- Monorepo: pnpm workspaces + Turborepo
- Frontend: Vite, React, TypeScript, ESLint, Prettier
- Backend: FastAPI, uvicorn, Ruff, Pyright, pytest, httpx
- Runtime config: environment variables with `.env.example` files

## Requirements

- Node.js 22+
- pnpm 10+
- Python 3.12+
- uv

## Getting Started

Install JavaScript dependencies:

```bash
pnpm install
```

Install backend dependencies:

```bash
cd apps/api
uv sync
```

Run both apps:

```bash
pnpm dev
```

Frontend: http://localhost:5173

Backend API: http://localhost:8000

Backend docs: http://localhost:8000/docs

## Quality Checks

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm format:check
```

Backend-only checks:

```bash
cd apps/api
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```
