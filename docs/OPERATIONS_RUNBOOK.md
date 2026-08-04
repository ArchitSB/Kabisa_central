# Operations runbook

## Health, logs, and audits

- Liveness: `GET /health` confirms the API process is running.
- Readiness: `GET /api/v1/health/ready` performs a database round trip.
- API logs are JSON in production and include request ID, actor ID when known,
  method, path, status, latency, and client IP. Preserve `X-Request-ID` through
  the reverse proxy.
- Managers and super-admins can use **Management → Audit log** to filter by
  actor, action, entity, date, and search term. Audit rows are read-only.
- Run `docker compose --env-file .env.prod -f docker-compose.prod.yml exec api
  python -m app.integrity` after migrations, large imports, or an incident.

## Backup and restore

The backup service writes a compressed custom-format dump every 24 hours and
retains 14 days by default. These are minimum defaults; copy backups off-host
and test restores regularly. Snapshot the uploads volume on the same schedule.

List database backups:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec postgres-backup ls -lh /backups
```

Restore into a new/empty database after stopping application writes:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml stop api
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres dropdb -U kabisa --if-exists kabisa_restore
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres createdb -U kabisa kabisa_restore
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres-backup pg_restore -h postgres -U kabisa -d kabisa_restore --clean --if-exists /backups/kabisa-TIMESTAMP.dump
```

Use the configured database/user and stage the dump in a mounted path. Validate
the restored database with the integrity command before changing a production
connection string.

## Common tasks

```bash
# Current migration and history
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api alembic current
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api alembic history

# Reconcile production-safe roles and reference data
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api python -m app.bootstrap

# Follow structured API logs
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f api
```

Do not run `python -m app.seed` in a live customer database; it includes the
development demonstration dataset. Create operational admins through the UI,
and preserve the last-super-admin and self-demotion safeguards.

## Incident outline

1. Preserve logs, request IDs, audit records, and database/upload snapshots.
2. Deactivate the affected admin; active-user checks make existing access
   tokens fail.
3. Rotate compromised credentials/secrets and restart the API.
4. Use audit filters plus request logs to bound affected entities.
5. Run integrity checks; restore only after validating the recovery point.
6. Record the cause, actions, and prevention follow-up outside the application.
