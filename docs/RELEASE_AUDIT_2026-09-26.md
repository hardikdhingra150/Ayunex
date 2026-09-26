# Release audit — 26 September 2026

## Release decision

**Local pilot, not approved for public production.** The previous Git commit title saying all modules were complete is not a release certification. This audit found and repaired material authentication, data isolation, consent, evidence and deployment issues. All four module specifications remain targets; checklists are not proof of completion.

## Changes implemented

- Added verified-email signup/login, HttpOnly revocable cookie sessions, CSRF/origin checks, rate-limited authentication and single-use password reset that revokes all sessions. Browser developer-token forms are removed. Built-in accounts are user-only; staff MFA remains an external integration gate. Schema 0005 adds account/session/action tables. See [hosting and accounts](HOSTING_AND_ACCOUNTS.md) for SMTP and deployment requirements. This supersedes external-identity-only wording below.

- Removed public role/subject/tenant selection. Local guests get unique user identities and tenants, one-hour signed tokens, and no privileged access. Local signing is disabled in production; production requires the external identity adapter.
- Removed development-token suffix privilege escalation, embedded frontend credentials, browser token persistence and default signing secrets. Rotated the local development token. Previously committed copies remain in history but the old local token no longer authenticates after restart. No history rewrite was performed.
- Restricted introspection to authenticated services; tenant-filtered audit listings. Serialized audit-chain appends and added a unique sequence index.
- Added migration 0004 for platform consent/audit tables; production startup no longer creates these tables. Unified readiness checks for migration state and Redis. Fixed static-file path traversal and added production CSP.
- Hosted AI consent starts unchecked. API calls require a matching active, purpose-specific consent record. Withdrawal blocks subsequent hosted requests. Already-dispatched external requests cannot be recalled.
- Browser API requests use the serving origin, with a Vite development proxy, instead of always calling the visitor's own localhost.
- Fixed source-name/free-text heuristics that silently marked formula, method, ingredient and processing conditions confirmed. Unknown decisive legal facts remain unknown.
- Explicit Section 3(p) queries prefer the exact provision; patent questions no longer select unrelated ABS documents solely through generic word matches.
- Production answers exclude SOURCE_TEXT_CHECKED pilot evidence. This label is not expert approval. An observed ABS Regulation 5 excerpt ended after the first table row and was quarantined locally, preserving its source and audit history. The repeatable quarantine command is development-only.
- Provider transport errors reveal only safe status information. HTTP 429 causes a 60-second per-process cooldown and immediate source-only fallback, not repeated repair calls. This is not a distributed quota or spending-cap system.
- Removed Naut IQ credits from rendered app/footer/title; retained historical team/project documents.
- Removed default deployment passwords, required explicit production identity/HTTPS settings, corrected the Docker build context, and added frontend CI checks.

## Verification

- Current regression results: 132 backend tests passed in both SQLite and PostgreSQL-backed runs, 31 frontend tests passed, lint/build passed, migrations through 0005 show no drift. Sign-in/signup forms checked in the local browser. npm production dependency audit and isolated `uvx pip-audit -r requirements.lock.txt` report no known vulnerabilities. These scans are not penetration testing or a security certification.

- SQLite backend regression suite, PostgreSQL-backed regression suite and migration drift checks executed locally (see final handoff for current test totals).
- Frontend lint, Node tests and production build executed; build still warns about large JavaScript chunks.
- Browser guest session and source-excerpt retrieval verified before account replacement, with AI consent initially unchecked. Account API regression tests now cover verification, cookie login/logout, CSRF, reset revocation and invalidated links; real SMTP delivery is not yet validated.
- A prior public Section 3(p) end-to-end check returned HOSTED_RAG using qwen/qwen3.8-27b. During this release audit Groq returned HTTP 429; the latest provider check therefore did **not** confirm fresh live generation. Do not describe the provider as currently unrestricted/always available.
- Temporary smoke case was deleted; non-secret consent/audit records remain. No personal user cases or source documents were deleted.
- Docker runtime, public TLS, real identity provider and backups/restore were not validated here.

## Module-by-module remaining gates

| Module | Implemented/tested foundation | Still required before broad production |
| --- | --- | --- |
| A | React/JS workspace, general live queries, opt-in case APIs, citations, explicit consent, safe guest connections | Real login/session recovery, complete live Passport round-trip and concurrent-save/browser tests, accessibility/mobile acceptance, validated multilingual content; remaining mock screens must remain labelled |
| B | Tenant/owner/role boundaries, case versions, deterministic unresolved routing, domain pointers, checklists/escalation/export APIs | Expert-reviewed rules and two product journeys; live facilitator operations; broader domain acceptance tests |
| C | Versioned seed documents, reviewed retrieval, cited synthesis/check/fallback, source provenance, safe abstention | Complete provision boundaries/tables, expert-approved corpus, later amendments, legal gold benchmark, Hindi/voice and international coverage, measured retrieval quality and distributed model budgets |
| D | Development guest isolation, external identity interface, consent/audit APIs, migration/deployment guards | Configure and verify real IdP/MFA and revocation, domain/TLS/hosting, trusted-proxy rate limiting, privacy/retention/provider deletion review, encrypted backup restore, monitoring/incident drills and load/security testing |

## Run and test

From the project root: `npm run backend` and (for development UI) `npm run frontend`.
The built app is served at `http://127.0.0.1:8000/`; sign in at `/login`. Built-in verified accounts persist across restarts. Without SMTP in development, open the private verification message in `backend/.mail-outbox/`. Production requires authenticated SMTP. Local guest endpoints are retained for explicit engineering tests only, not the browser account experience.

From `backend/`: `.venv/bin/python -m scripts.smoke_live --execute` explicitly permits a public-question provider test and may incur provider costs. A safe source-only fallback fails that test's HOSTED_RAG assertion by design.

For the observed incomplete ABS seed: `.venv/bin/python -m scripts.quarantine_incomplete_seed --apply`. No blanket source approvals are performed.

Never commit `.env`, `.dev-token`, databases, raw credentials or personal case data. Do not point production identity introspection at the local guest token endpoint. Configure trusted proxy addresses before relying on per-client rate limits behind a reverse proxy.
