# AYUNEX · Naut IQ

Ayurveda intellectual-property and regulatory research workspace · SIH 26045.

## Run

```sh
npm run backend          # local API: http://127.0.0.1:8000/docs
npm run frontend         # React app, in a second terminal
npm run backend:test     # automated backend checks
npm run module-c:evaluate # synthetic retrieval/citation checks; not legal accuracy
npm run corpus:list      # public-source catalog and access restrictions
npm run corpus:sync      # bounded official PDF ingestion; network required
```

One-time backend setup and authentication: [backend README](backend/README.md). The UI remains mock-first until explicitly connected; no browser case data is silently uploaded.

## Where things live

| Folder | Purpose |
| --- | --- |
| `frontend/` | React/JavaScript application and its tests |
| `backend/` | API, domain logic, corpus pipeline, database migrations and tests |
| `data/corpus/` | Official-source catalog, ingestion report and content-addressed raw PDFs |
| `docs/` | Idea, research, blueprint, module specifications and production readiness |
| `presentations/` | Existing PPT deliverables, preserved with original filenames |
| `deploy/` | Non-root container, PostgreSQL/Redis/TLS proxy deployment configuration and runbook |
| `scripts/` | Short root-level commands |
| `archive/` | Older presentation-build work and unused frontend themes; recoverable, not deleted |

## Read first

- [Production readiness and known gaps](docs/PRODUCTION_READINESS.md)
- [Deployment runbook](deploy/README.md)
- [Corpus scope and evidence policy](data/corpus/README.md)
- [Four module specifications](docs/modules/README.md)
- [Module C implementation status](docs/modules/MODULE_C_IMPLEMENTATION_STATUS.md)
- [Hosted AI setup and live-validation gates](docs/HOSTED_AI_SETUP.md)
- [Detailed idea](docs/IP-SAKTI_DETAILED_IDEA.md)

**Information, not legal advice.** Downloaded official text is not automatically reviewed/current/applicable evidence. Restricted TKDL content and registry bulk data are not included. A live production release still requires identity/hosting configuration, legal review and operational acceptance testing.
