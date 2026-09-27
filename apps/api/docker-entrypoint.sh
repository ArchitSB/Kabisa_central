#!/bin/sh
set -eu

alembic upgrade head
python -m app.seed.storefront
exec "$@"
