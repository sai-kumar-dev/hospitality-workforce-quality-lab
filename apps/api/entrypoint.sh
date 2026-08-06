#!/bin/sh
set -eu

alembic -c /app/apps/api/alembic.ini upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    python -m shiftbridge_api.db.seed
fi

exec uvicorn shiftbridge_api.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --no-access-log
