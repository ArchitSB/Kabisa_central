# Kabisa Admin Panel

Tier 1 of Kabisa Pharmacy's digital platform: a FastAPI and React operations
workspace for catalog, inventory, customers, orders, delivery, and payments.

This repository contains the Phase 0 foundation and Phase 1 authentication
and role-based access control. The admin shell uses real administrator
sessions and server-enforced permissions. Domain workflows still use
representative preview data until their scheduled phases.

## Requirements

- Python 3.12
- Node.js 20+ and pnpm 10
- Docker with Compose v2

If pnpm is not installed, enable it through Corepack:

```bash
corepack enable
corepack prepare pnpm@10.14.0 --activate
```

## Start locally

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

   - API docs: `http://localhost:8000/docs`
   - Liveness: `http://localhost:8000/health`
   - PostgreSQL readiness: `http://localhost:8000/api/v1/health/ready`

4. Configure and seed the Phase 1 administrator.

   Set `JWT_SECRET_KEY` and replace the placeholder
   `SUPER_ADMIN_PASSWORD` in `.env`. The configured
   `SUPER_ADMIN_EMAIL` is the sole developer super-admin identity. Then run:

   ```bash
   python -m app.seed
   ```

   The seed refuses the documented placeholder or passwords shorter than 8
   characters. It is safe to re-run: the five system roles, permission
   catalogue, mappings, and configured super-admin are reconciled without
   duplicates. Re-running with a changed `SUPER_ADMIN_PASSWORD` updates the
   seeded administrator password.

5. Install and start the admin web.

   ```bash
   pnpm install
   pnpm dev:web
   ```

   Admin login: `http://localhost:5173/login`

## Authentication and first login

- Sign in with the `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` configured in
  the local `.env`. Passwords are never committed, logged, or returned.
- The developer super-admin can create operational administrators under
  **Management → Admin users**, set an initial password, and assign a role.
- Every account that can sign in is an `admin_users` record. Customer
  authentication is separate and is not accepted by these endpoints.
- Inactive or soft-deleted administrators cannot sign in, and an existing
  access token is rejected after deactivation.
- The developer-only **Viewing as** switcher previews the five seeded system
  roles in the browser. It only reduces the effective UI permission set; API
  authorization always uses the signed-in user. Set
  `VITE_ENABLE_ROLE_SWITCHER=false` outside developer environments.
- Access tokens expire after 30 minutes by default. The web client performs one
  transparent refresh with the seven-day refresh token, then returns to
  `/login` if the session cannot be restored.
- SQL statement logging is disabled by default. Enable `DB_ECHO` only for
  focused local database debugging.

The Phase 1 API is under `/api/v1`:

```text
POST /auth/login
POST /auth/refresh
GET  /auth/me
POST /auth/logout
GET|POST /admin-users
GET|PATCH|DELETE /admin-users/{user_id}
GET|POST /roles
GET|PATCH|DELETE /roles/{role_id}
GET /roles/permissions
```

All non-authentication management routes independently enforce their required
permission. Expected API errors use `{ "detail": "...", "code": "..." }`.

## Quality commands

```bash
pnpm lint
pnpm typecheck
pnpm build
ruff check apps/api
black --check apps/api
pytest apps/api/tests
```

Backend tests use the isolated database configured by `TEST_DATABASE_URL` and
never drop application tables from `DATABASE_URL`.

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
