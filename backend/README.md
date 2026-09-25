# AYUNEX — Module B

**25 September:** [Hosted provider setup](../docs/HOSTED_AI_SETUP.md), optional OCR, structural parsing, model-versioned vector/lexical fusion and bounded synthesis/verification are implemented. `npm run provider:check` is offline; hosted processing remains disabled without credentials and explicit consent. The expanded suite passes 100 tests. Migration 0003 is applied by the local launcher.

**24 September:** Module C local retrieval is connected. [Implementation status](../docs/modules/MODULE_C_IMPLEMENTATION_STATUS.md) explains exact-quote guidance, eligibility filters and remaining semantic-RAG work. Use `npm run module-c:evaluate` for reproducible synthetic safety checks. Corpus review revocation now invalidates stored local answers and downloads. Upstream identity/guidance responses are size-bounded while streaming.

**Latest delivery:** See [production readiness](../docs/PRODUCTION_READINESS.md) and [deployment runbook](../deploy/README.md). The September 23 update adds the reviewed-corpus API, official PDF ingestion, request hardening and deployment files. Hosting is deferred; this is not a certified production release.

Local startup defaults to `GUIDANCE_MODE=corpus`: only currently reviewed original passages can support extractive guidance. The imported seed is unreviewed, so abstention is expected. To inspect pending sources, use `/api/v1/corpus/search` with `reviewed_only=false` and an explicit `as_of` date. `npm run corpus:list` lists configured sources; `npm run corpus:sync` acquires public PDFs and records failures. A local development token cannot approve legal passages.

FastAPI, Pydantic, SQLAlchemy 2, Alembic; SQLite for an immediate local run and PostgreSQL for deployment. The app uses no LLM to choose a product category.

## Start locally

**Simplest command — from the project root:**

```sh
npm run backend
```

`npm start` is an alias. No Python environment activation is needed. Check installed dependencies with `npm run backend:check`.

The project virtual environment has been installed. From this directory:

```sh
.venv/bin/python dev.py
```

API documentation: http://127.0.0.1:8000/docs

The launcher applies migrations and creates a private `.dev-token` file with owner-only permissions. Use Swagger’s **Authorize** button and paste the token (without the `Bearer` prefix), or send `Authorization: Bearer <token>` from an API client. This credential only represents the `local-developer` user in the `local-demo` tenant; it never grants administrator or facilitator access. Never commit or send this token. Swagger exposes the HTTP Bearer security scheme through the shared identity dependency.

For a fresh installation:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python dev.py
```

Do not use real confidential product details during local development: local SQLite is not an encrypted production vault.

## Implemented services

- Authenticated case CRUD, archive/restore, tenant and owner isolation, optimistic revisions.
- Immutable Passport versions; structured ingredients, provenance, unknown values, extracted-fact confirmation and contradiction detection.
- Versioned deterministic three-valued decision tables. All bundled legal routes are **UNVALIDATED** and therefore never yield a supported legal classification.
- Ranked English/Hindi clarification templates, up to three questions per batch; explicit Unknown is not repeatedly asked.
- National/treaty/export context separation, context hashes and stale-result flags.
- Seven independent IP research routes, unresolved ABS checks, TKDL/public prior-art pointers, regulatory and treaty retrieval requests.
- Route-specific preparation checklists. Checking an item never establishes compliance.
- Module C HTTP adapter with timeouts, strict response schemas, jurisdiction/effective-date/citation checks, public-only access, idempotent case guidance and verified-result SSE replay. It does not proxy unverified model tokens.
- Consented local review queue with facilitator role enforcement, reviewer comments, withdrawal and context-change revocation. No external email/delivery is claimed.
- Search notes, snapshot exports, export deletion/retention, activity records and transactional domain-event outbox.
- OpenAPI contract and an opt-in JavaScript integration client in `frontend/src/backendClient.js`.

## Local API sequence

1. `POST /api/v1/cases` with title, jurisdiction, date and `case-notice-v1` acknowledgement.
2. Save `POST /cases/{id}/passport/answers` with `expected_revision` and the complete Passport snapshot.
3. Call `/classify`, `/clarifications` and `/domains`. Results explain unresolved conditions and retrieval needs.
4. Call `/checklists` or `/escalations` with explicit sharing consent.
5. `/guidance` requires a configured Module C service and `Idempotency-Key`. Missing Module C returns **503**, never synthetic legal text.
6. `/exports` creates an export snapshot; download through `/exports/{id}`.

All business routes have `/api/v1` prefix. Reload the case after a **409** and reconcile against its latest revision; do not blindly overwrite newer changes. Reuse a guidance idempotency key only for an identical request and unchanged case context.

### Create-case example

```json
{
  "title": "Synthetic food concept",
  "query_kind": "PRODUCT_SPECIFIC",
  "jurisdiction": {"layer": "NATIONAL", "country": "IN"},
  "as_of_date": "2026-09-23",
  "consent": {"accepted": true, "notice_version": "case-notice-v1"}
}
```

### Passport example

```json
{
  "expected_revision": 2,
  "passport": {
    "facts": {
      "intended_use": {"value": "FOOD", "provenance": "user-entered"},
      "food_subroute": {"value": "AYURVEDA_AAHARA"},
      "origin": {"unknown": true}
    },
    "ingredients": [{"name": "Synthetic ingredient", "biological_type": "PLANT", "origin": "UNKNOWN"}]
  }
}
```

Use the returned revision, not the example's literal number.

## Module C/D contracts

Configure environment variables in your process (the `.env.example` file is documentation, not loaded automatically):

- `IDENTITY_INTROSPECTION_URL`: HTTPS Module D endpoint accepting `{ "token": "..." }`; respond `{ "active": true, "principal": { "subject": "...", "tenant": "...", "role": "user" } }`. D must validate expiry, issuer, audience, revocation and membership. `IDENTITY_SERVICE_TOKEN` authenticates B to D.
- `GUIDANCE_SERVICE_URL`: HTTPS endpoint accepting the context-bound structured request documented in `app/main.py`. Respond with `GuidanceAnswer` from OpenAPI; echo exact request ID, context hash, jurisdiction and date. `GUIDANCE_SERVICE_TOKEN` authenticates B to C.
- Access classes are currently server-fixed to `PUBLIC`; paid/TKDL access remains denied. A later D grant integration must not trust access classes from frontend input.
- `DATABASE_URL`: PostgreSQL SQLAlchemy URL, e.g. `postgresql+psycopg://...`.
- `APP_ENV=production` disables local-token authentication and requires PostgreSQL, HTTPS identity and explicit HTTPS CORS origins.

The current React interface remains intentionally mock-first. The new client is not automatically switched on, and no existing browser data is silently uploaded. Full A→B→C→D activation is a separate integration step.

## Storage and privacy

Cases, immutable snapshots, artifacts and outbox events are stored transactionally. Artifacts consolidate classification/checklist/escalation/export records in typed JSON envelopes instead of premature tables for every domain; schemas and database uniqueness constraints validate the application boundary. Ingredients remain in their exact versioned Passport snapshot, preserving ambiguous aliases rather than silently equating botanical names.

Deletion cascades through all case-owned database rows, including local exports. It cannot delete files a user already downloaded or erase database backups. Module D must own backup retention, encryption, deployment controls, durable audit delivery, identity and consent-ledger integration. The outbox is a transactional integration seam, not an already delivered external audit record.

Retention preview (no deletion by default):

```sh
.venv/bin/python -m scripts.retention --export-days 30
# Only after reviewing the dry-run result:
.venv/bin/python -m scripts.retention --export-days 30 --apply
```

## Checks and contracts

```sh
.venv/bin/python -m pytest -q
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/python -m scripts.export_openapi
```

For isolated PostgreSQL tests, set `TEST_POSTGRES_URL` to a disposable test database. Tests create and drop a unique schema per fixture; never point this at production.

Read [MODULE_B_STATUS.md](MODULE_B_STATUS.md) for verified coverage and explicit completion boundaries.
