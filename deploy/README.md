# Deployment runbook — prepared, not deployed

Run commands from the project root. Hosting, DNS, identity provider and real credentials are intentionally not selected. Docker is required; the container stack has not been executed on this workstation.

## Configure

1. Copy `deploy/production.env.example` to `deploy/.env.production` using your editor. Keep the latter out of version control and restrict its permissions. Replace every placeholder; use separate, randomly generated secrets. URL-encode passwords inside connection URLs.
2. Point the chosen API hostname at your server. Allow HTTPS/HTTP only; never publish PostgreSQL or Redis ports. Set the exact HTTPS frontend origin.
3. Implement/configure the identity introspection contract documented in `backend/README.md`. The production API refuses local development tokens. The introspection service must authoritatively return subject, tenant and role; never accept browser-supplied roles.
4. Keep `GUIDANCE_MODE=corpus` for reviewed extractive source discovery. External synthesis requires a separately implemented and validated guidance service. Neither mode makes unreviewed classification rules legally reliable.

## Build and start

```sh
docker compose --env-file deploy/.env.production -f deploy/compose.yml config --quiet
docker compose --env-file deploy/.env.production -f deploy/compose.yml build
docker compose --env-file deploy/.env.production -f deploy/compose.yml up -d
docker compose --env-file deploy/.env.production -f deploy/compose.yml ps
```

The migration job runs before API startup. Caddy terminates TLS. The API is non-root, read-only except temporary files and its corpus volume. Database and corpus data persist in named volumes. Do not run `down -v` on a real installation.

## Acquire and review evidence

```sh
docker compose --env-file deploy/.env.production -f deploy/compose.yml exec api python -m scripts.ingest_corpus
```

Downloads are allowlisted, size/time bounded and hash-versioned. Inspect the report in the corpus volume. A failed source is not silently considered imported. Importing never approves evidence. A qualified reviewer must use the role-protected passage review API with exact provision, effective dates, review expiry, notes and expected checksum. Restricted TKDL is a pointer only; no credential bypass or bulk registry scraping is implemented.

## Release checks

- Verify `/health/readiness`, identity rejection/acceptance, tenant isolation, review permissions, CORS and HTTPS from the actual domain.
- Exercise Redis failure, migration failure and recovery. Readiness checks schema/database and the configured Redis service, not identity availability or legal evidence coverage. Monitor these separately.
- Proxy headers are deliberately disabled. The rate limiter sees the proxy IP, so the configured limit is shared behind Caddy. Before public traffic, configure a strictly trusted proxy chain and test spoof rejection, or provide verified-identity rate limiting. Do not blindly trust arbitrary forwarded headers.
- Pin container image digests, run dependency/image scans and load tests, configure resource sizing, alerting, log retention and incident procedures for the selected host.
- Export PostgreSQL with `pg_dump` through your deployment tooling. Encrypt backups, store them separately from the server and test restoration to an isolated database. Also back up raw corpus files and deployment configuration; never publish credentials.
- Rehearse rollback on a staging database. Take a verified backup before migrations; do not downgrade a live schema without reviewing data-loss implications.
- Schedule corpus refresh and expert review. Add the missing drug, food, advertising, IP-type and international sources before claiming full problem-statement coverage.

See `docs/PRODUCTION_READINESS.md` for explicit limits. Deployment files are a starting configuration, not security certification or a completed production release.
