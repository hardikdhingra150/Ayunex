# Module B delivery and release gates

**25 September update:** 100 regression tests pass, including the PostgreSQL-backed run and migration 0003 checks. Curator reviews now use atomic revisions; reparsing and hosted answers retain evidence-revocation protection. Hosted Module C integration is implemented behind opt-in configuration and request permission. See [current readiness](../docs/PRODUCTION_READINESS.md) and [provider setup](../docs/HOSTED_AI_SETUP.md). No live provider/identity validation, expert legal approval or production deployment is claimed.

**24 September update:** [Current cross-module release checklist](../docs/PRODUCTION_READINESS.md). The expanded backend suite passes 80 tests; PostgreSQL-backed regressions and migration drift checks also pass. Five official PDF sources are indexed, all pending review. Module C's local retrieval/citation baseline is connected; revocation invalidates stored evidence and upstream responses are stream-size-bounded. Container deployment remains unexecuted until Docker/hosting and identity are configured. Older test counts below describe the earlier core milestone.

23 September 2026 · AYUNEX / Naut IQ / SIH 26045

## Honest completion status

The executable backend core is implemented and locally testable. **The complete original Module B definition of done is not yet 100% satisfied:** it requires expert-reviewed legal journeys, live Module C evidence services and Module D identity/consent infrastructure. No credentials or expert-approved rules were supplied. These requirements are explicit release gates, not replaced with fake approvals.

## Implemented engineering coverage

| Area | Delivered |
| --- | --- |
| B1 Identity | Module D introspection adapter; fail-closed verification; tenant/owner/role checks; isolated development credential; production startup guard |
| B2 Cases | Persistent CRUD, archive/restore, revision conflicts, timestamps, transaction-linked outbox |
| B3 Passport | Structured validation, immutable snapshots, provenance, unknowns, confirmed extracted facts, contradiction detection |
| B4 Classification | Deterministic JSON decision table; all seven candidate branches exercised; three-valued conditions; unvalidated rules never return approved routes |
| B5 Clarification | Ranked English/Hindi templates, maximum three questions, no repeated explicit Unknowns, general-query bypass |
| B6 Firewall | Explicit country/framework contexts; date/version hashes; stale artifacts and consent invalidation |
| B7 IP strategy | Seven independent research routes; missing facts and review states; no patent grant prediction |
| B8 ABS | Applicant/resource/origin/activity/TK/exception gaps; no default exemption or clearance |
| B9 TK/prior art | Public pointers, structured search query, saved search notes; restricted TKDL remains inaccessible |
| B10 Regulation | Separate candidate routes and evidence retrieval/preparation requests; no unverified licence/form assertions |
| B11 International | Named treaty versus country contexts; unsupported-market abstention; treaty status explicitly unknown without evidence |
| B12 Actions | Preparation checklists, status edits, portal directory, exports and dry-run-first retention |
| B13 Escalation | Review recommendation and consent-gated packet, local queue, role-gated comments, withdrawal, context-change revocation |

## Verification

- 50 backend tests pass on SQLite and the same 50 pass on isolated PostgreSQL 16.
- Tests cover tenant/role isolation, revisions, version history, branches, contradiction/Unknown handling, evidence firewall, service failure/timeout, idempotency, stale requests, consent and cascade deletion.
- Alembic migration and schema-drift checks run on both databases.
- Existing frontend build/lint and 28 frontend/adapter tests pass.
- OpenAPI is exported to `openapi.json`; Swagger includes Bearer authorization and typed request/core-response models.
- PostgreSQL test data is isolated from the user's existing databases; test schemas are cleaned after each run.
- A non-fatal upstream Starlette/httpx TestClient deprecation warning remains. No production request failure was observed from it.
- Live HTTP smoke checks passed: health, create, classify, clarify, checklist, export and deletion of the synthetic test case. Unconfigured guidance correctly returned 503.

## Not claimed complete

1. Expert-reviewed rules, dated provision evidence and two reviewed legal gold journeys. All bundled routing tables deliberately remain UNVALIDATED.
2. Real Module C retrieval, authority verification and evaluated multilingual legal guidance. Absent service returns 503; tests use explicitly synthetic fixtures.
3. Real Module D identity, durable consent ledger, paid-source grants, external audit delivery, encryption/backup retention, deployment security and live facilitator notifications.
4. Full Module A live-mode wiring. An explicit JavaScript client is provided; the user's existing frontend remains labelled mock mode, with no silent data upload.
5. Production load/security testing, independent legal/Hindi review, verified current form metadata and country-specific legal adapters.

The data model deliberately consolidates related records into versioned JSON artifacts and immutable Passport snapshots rather than implementing every suggested table literally. Database foreign keys, unique idempotency keys, optimistic revisions and Pydantic validation protect these boundaries.

## What you need to provide later

- Module C service URL/token, or authorization to build Module C next.
- Module D identity/consent integration when that module is ready.
- A qualified reviewer to validate the two starting product journeys and source-linked rule conditions.

No paid API key is required to exercise the local core or run tests.
