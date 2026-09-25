# AYUNEX — delivery and release gates

Updated 25 September 2026. Hosting deferred by the project owner.

## Latest B/C work

Hosted OpenAI/Gemini adapters, model-versioned embeddings, bounded vector/lexical fusion, evidence-only synthesis, a separate model-verification pass and one repair are implemented behind explicit configuration/request permission. No hosted credentials are configured and no live paid calls have been made. See [hosted setup](HOSTED_AI_SETUP.md).

Provision-candidate parsing, optional bounded OCR, non-destructive reparse and optimistic curator review updates are implemented. Tesseract is not installed natively, so actual OCR remains untested. Source table structure/locator correctness must be visually reviewed. The five PDFs now have 553 active parsed segments and 338 inactive historical segments; zero are legally approved.

## Implemented locally

- Case lifecycle, revision checks, jurisdiction separation, formulation fact collection, clarification, domain routing, checklists, citation schemas, exports, consent-scoped human review and audit records.
- PostgreSQL-compatible persistence and explicit Alembic migrations; local SQLite development launcher.
- Role/tenant authorization boundaries, production identity adapter, shared Redis rate-limit support, bounded requests, host/CORS restrictions, safe error responses, request IDs and metadata-only request logging.
- Allowlisted official-PDF acquisition, content hashes, immutable source versions, page passages, supersession, curator-only reviews with checksums/effective intervals/expiry, and review audit records.
- Authenticated source discovery and conservative extractive guidance. No approved matching evidence means abstention, not generated authority. This is not a complete multilingual semantic RAG implementation.
- Docker, PostgreSQL, Redis and Caddy deployment configuration, with non-root API and explicit migration startup.

## Verification performed

- Backend: 100 automated tests passed on SQLite. The PostgreSQL-backed regression run also passes; schema-backed case/corpus tests use isolated PostgreSQL schemas (database-independent and rate-limit-only tests retain their own fixtures). PostgreSQL migration 0003 and drift check passed; OpenAPI regenerated.
- Module C: 50 synthetic engineering checks pass via `npm run module-c:evaluate`; expert legal accuracy remains unmeasured. Real external HTTP is forbidden in regression tests.
- Frontend: 28 tests passed; lint and production build passed. Build still warns about JavaScript chunks above 500 kB.
- Dependency launcher check passed. The current Docker stack has not been built or run here (Docker is unavailable). Current corpus migration has not yet been revalidated against a hosted PostgreSQL deployment.

## Dataset acquisition results

Five official PDFs indexed: Patents Act compilation, two 2024 patent rule notifications, NBA ABS Regulations 2025 and NBA resource-classification guidance. These yielded 161 pages and originally 338 passages; the reparse counts are above. All are pending legal review. Two FSSAI attempts failed PDF/content-coverage checks and are not counted as indexed evidence. See `data/corpus/ingestion-report.json` for original acquisition results.

The India Code biodiversity PDF timed out. India Code migration and registry links remain discovery pointers. Full TKDL is restricted and has not been downloaded. The catalog is a curated seed, not the full Ayurveda/IP/regulatory corpus; later amendments may supersede these documents.

## Still required before a public production release

1. Choose hosting/domain, real identity provider, secret management and operating owners. Validate the container stack, TLS and backups on staging; no live deployment has occurred.
2. Expert-review the classification rules and legal test cases. Existing routing candidates are explicitly unvalidated and must not be marketed as legal determinations or ABS clearance.
3. Expand and review the authoritative corpus: drug/food/cosmetic/advertising rules, other IP regimes, case law, treaties and individual export markets. Establish refresh/revocation responsibilities.
4. Complete and evaluate Module C retrieval/synthesis and multilingual translation if required. Current bounded lexical retrieval is suitable for a seed corpus, not a proven large-scale semantic search service.
5. Integrate real Module D identity and wire the frontend to production APIs. The frontend remains mock-first; the opt-in API client is not full end-to-end integration.
6. Local-corpus revocation/expiry now invalidates stored answers, SSE and export downloads; regression tests cover it. Extend freshness checks to the future external synthesis provider. Historical downloaded exports cannot be recalled and must carry dates and limitations.
7. Complete independent security/privacy review, retention/deletion policies, threat modelling, accessibility/internationalization QA, load/failure tests, monitoring and restore drills. No DPDP or AI-standard certification is claimed.
8. Resolve trusted-proxy rate limiting before public traffic; currently requests behind the proxy share its IP budget.

The backend has a tested local foundation and prepared deployment files. It is **not yet a fully validated production service**. No credentials or legal approvals have been invented to remove these gates.
