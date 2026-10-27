#!/bin/sh
set -eu

# Run schema/demo provisioning explicitly during deployment, not on every restart.
if [ "${KABISA_RUN_MIGRATIONS:-false}" = "true" ]; then
    alembic upgrade head
fi
if [ "${KABISA_SEED_DEMO:-false}" = "true" ]; then
    python -m app.seed.storefront
fi
exec "$@"
