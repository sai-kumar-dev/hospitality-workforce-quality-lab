# Infrastructure

The production-like local stack is intentionally defined in the root `compose.yaml` so Docker
Compose commands need no extra file flags.

- PostgreSQL is reachable only on the named Compose network.
- FastAPI waits for database health, runs Alembic, seeds idempotent fictional data in development,
  and starts without source reload.
- The web image contains compiled Vite assets and proxies `/api` to FastAPI.
- Application images run as non-root users and expose explicit health checks.

Runtime values come from `.env`; `.env.example` contains local-only demonstration defaults.
