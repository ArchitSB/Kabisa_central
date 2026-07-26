# Kabisa Admin Panel

Tier 1 of Kabisa Pharmacy's digital platform: a FastAPI and React operations
workspace for catalog, inventory, customers, orders, delivery, and payments.

This repository currently contains **Phase 0 — Foundations**. The admin shell
uses representative local preview data; authentication and live domain data
begin in Phase 1 and later checkpoints.

## Requirements

- Python 3.12
- Node.js 20+ and pnpm 10
- Docker with Compose v2

If pnpm is not installed, enable it through Corepack:

```bash
corepack enable
corepack prepare pnpm@10.14.0 --activate
```

## Start Phase 0

1. Create local configuration.

   ```bash
   cp .env.example .env
   ```

2. Start PostgreSQL 16.

   ```bash
   docker compose up -d postgres
   ```

   Add `--profile tools pgadmin` to include pgAdmin at
   `http://localhost:5050`.

3. Create the API environment and install the backend.

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -e "apps/api[dev]"
   alembic -c apps/api/alembic.ini upgrade head
   uvicorn app.main:app --app-dir apps/api --reload
   ```

   API docs: `http://localhost:8000/docs`  
   Liveness: `http://localhost:8000/health`  
   PostgreSQL readiness: `http://localhost:8000/api/v1/health/ready`

4. Install and start the admin web.

   ```bash
   pnpm install
   pnpm dev:web
   ```

   Admin preview: `http://localhost:5173`

## Quality commands

```bash
pnpm lint
pnpm typecheck
pnpm build
ruff check apps/api
black --check apps/api
pytest apps/api/tests
```

## Repository map

```text
apps/api/          FastAPI, async SQLAlchemy, and Alembic
apps/admin-web/    React 18, Vite, Tailwind, and shadcn-style primitives
packages/shared/   generated OpenAPI types destination
design-system/     quantified Kabisa design DNA and global design rules
```

The design source of truth is
[`design-system/MASTER.md`](design-system/MASTER.md). The machine-readable
profile is
[`design-system/kabisa-admin.dna.json`](design-system/kabisa-admin.dna.json).

