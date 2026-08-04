FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UPLOADS_DIR=/var/lib/kabisa/uploads
WORKDIR /app

RUN groupadd --system kabisa \
    && useradd --system --gid kabisa --home-dir /app kabisa \
    && mkdir -p /var/lib/kabisa/uploads \
    && chown -R kabisa:kabisa /app /var/lib/kabisa

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels
COPY --chown=kabisa:kabisa apps/api/alembic ./alembic
COPY --chown=kabisa:kabisa apps/api/alembic.ini ./alembic.ini
COPY --chown=kabisa:kabisa apps/api/docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod 0555 ./docker-entrypoint.sh

USER kabisa
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
