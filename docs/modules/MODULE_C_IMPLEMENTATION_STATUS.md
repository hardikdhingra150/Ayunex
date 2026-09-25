# Module C — implementation and validation status

Updated 25 September 2026. Working code is delivered; the complete specification and production acceptance are **not yet satisfied**.

## Implemented

- Local reviewed-excerpt guidance and opt-in hosted generation adapters for OpenAI and Gemini. Fixed official endpoints, size/time budgets, typed structured outputs and server-side keys.
- Server permission plus per-request `allow_hosted_processing` required for hosted calls. Prompts contain the permitted question, jurisdiction/date and public evidence, not private Passport fields.
- Model-versioned embeddings, exact cosine retrieval over eligible stored vectors, lexical ranking and reciprocal-rank fusion. Metadata filters precede candidate limits. This small-corpus engine is not pgvector/ANN or a large-scale search implementation.
- Cited atomic claims, mechanically bound original quotations/URLs/dates, a separate model verification pass and one repair maximum. Failed synthesis falls back to fresh exact excerpts. Model verification remains fallible; outputs stay review-required.
- Versioned official source acquisition, checksums, public-access restrictions, supersession and source-review expiry.
- Conservative provision-candidate parsing, page/character locators, continuation preservation and oversize quarantine. Inferred headings and table reading order require visual review.
- Optional Poppler/Tesseract OCR, bounded to 20 low-text pages per document with confidence checks. Native Tesseract is not installed here; real OCR is not yet validated. Docker dependencies are prepared.
- Non-destructive reparse: old passages become inactive history and new segments require fresh review.
- Curator-only inspection/review and review-history endpoints; atomic review revisions reject conflicting writes.
- Evidence revocation invalidates saved local/hosted answers, verified SSE, idempotent reuse and old export downloads. Regenerated exports flag historical stale records.
- Reproducible synthetic evaluations and CI configuration. Tests prohibit real external HTTP.

## Verification

All **100 regression tests pass** in the SQLite run and PostgreSQL-backed run. Database-dependent case/corpus tests use isolated PostgreSQL schemas; other tests use their own fixtures. Migration 0003 and model/schema drift checks pass.

The focused corpus/Module C evaluation passes **50 synthetic engineering checks**. These do **not** measure legal accuracy, real model quality, Hindi consistency or production performance. Provider fixtures test wire formats and failure handling, not live account compatibility.

## Dataset reality

Five official PDFs / 161 pages. Structural reparsing produced **553 active segments**, with **338 inactive historical segments** retained. One active segment is quarantined. **Zero passages are legally approved.**

India Code acquisition remains incomplete. FSSAI's 2022 notification acquisition returned non-PDF content; the downloaded 2025 order could not be indexed because of insufficient text coverage. The large scanned compilation is not covered by the bounded automatic OCR workflow. TKDL restricted content has not been imported. Corpus coverage remains substantially incomplete.

## Run and configure

```sh
npm run backend
npm run backend:test
npm run module-c:evaluate
npm run provider:check
npm run corpus:index
```

The last two commands are offline/dry-run by default. Evaluation reports are in `backend/reports/`. Synthetic approvals exist only in test databases, never in the real corpus.

See [hosted provider setup](../HOSTED_AI_SETUP.md) before setting credentials or requesting paid execution. Restart the backend to load changed code/settings.

## Remaining before full completion

1. Select and configure the provider/model IDs/key; validate live generation and embeddings against account permissions, budgets and data terms.
2. Acquire and curate the missing national and international corpus. Legally review exact provisions, effective dates, exceptions, conflicts and classification rules.
3. Install and validate OCR; complete table-preserving extraction and a reviewed correction workflow for ambiguous/oversized/scanned segments.
4. Benchmark retrieval and model-verification quality; implement scalable FTS/pgvector/reranking if measured corpus/traffic requires it. The current exact-vector limit is 5000 eligible vectors.
5. Complete reviewed Hindi glossary/translation and separate treaty/export coverage. These requests currently abstain.
6. Run expert-labelled held-out legal evaluations, multilingual tests, failure/load/security tests and real frontend/identity integration.
7. Add later-phase graph and licensed connectors only with permissions and demonstrated benefit.

No live provider calls, legal approval, deployment certification or complete dataset is claimed.
# Groq integration update — 25 September 2026

Groq generation is implemented with Qwen `qwen/qwen3.8-27b`, strict structured output for supported models, bounded transport, local citation checks, request consent and safe local fallback. Groq uses lexical retrieval; no embedding endpoint is assumed. Offline backend suite: **111 passed**. Local configuration check: provider not selected, key absent; **live connectivity has not been tested**. See `../HOSTED_AI_SETUP.md` for replacement-key setup. The Qwen model is preview, not a production release guarantee.

This update does not close the existing legal/corpus review, coverage, multilingual quality, identity integration or live deployment gates below. No production-completion claim is made.
