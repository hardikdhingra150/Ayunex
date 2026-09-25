# Hosted Module C setup

Prepared 25 September 2026. No real provider calls have been made. OpenAI, Gemini and Groq adapters have offline transport tests; validate with your account before using them.

## Selected provider: Groq

Revoke the key shared in chat and create a replacement. Save it only in `backend/.env` using these settings; do not overwrite unrelated existing settings:

```dotenv
GUIDANCE_MODE=hosted
AI_PROVIDER=groq
AI_API_KEY=YOUR_REPLACEMENT_KEY
AI_GENERATION_MODEL=qwen/qwen3.8-27b
AI_EMBEDDING_MODEL=
CLOUD_PROCESSING_ALLOWED=true
```

Run `npm run provider:check` for an offline configuration check, then `npm run provider:check -- --execute` for a paid, synthetic generation test. Start/restart with `npm run backend`. Request-level `allow_hosted_processing=true` is still required. No key has been saved from chat.

Groq's [model catalog](https://console.groq.com/docs/models) lists this exact Qwen model as **preview**, not production. The adapter uses its [strict structured outputs](https://console.groq.com/docs/structured-outputs), and still validates citations and model output locally. Other Groq models use JSON mode unless explicitly listed as strict-capable in the adapter. Groq here is generation-only: approved lexical evidence is retrieved locally; there is no configured Groq embedding endpoint. A successful connectivity test does not certify legal accuracy, retrieval quality or production readiness.

## 1. Configure secrets locally

Create `backend/.env` in your editor, using `backend/.env.example` as a reference. Do not overwrite an existing configuration. This file is ignored by Git. Never put API secrets in frontend code, `VITE_*` variables, screenshots or chat.

```dotenv
GUIDANCE_MODE=hosted
AI_PROVIDER=openai
AI_API_KEY=your-server-side-key
AI_GENERATION_MODEL=your-compatible-generation-model-id
AI_EMBEDDING_MODEL=your-compatible-embedding-model-id
CLOUD_PROCESSING_ALLOWED=true
```

Use `AI_PROVIDER=gemini` for Gemini. Model IDs must be compatible with structured JSON output and embeddings respectively. Model access, prices, region, retention and data-processing terms must be checked for your account; no default paid model has been selected.

The local launcher loads `.env` without shell expansion; existing process environment values take precedence. Production Compose uses `deploy/.env.production`, not the development file.

## 2. Check before spending

```sh
npm run provider:check
```

This prints only configuration presence, never the key, and makes no network request.

After checking billing and data terms, a small paid connectivity test can be explicitly requested:

```sh
npm run provider:check -- --execute
```

It sends synthetic text only. Passing it verifies connectivity/schema compatibility, not legal accuracy or model quality.

## 3. Review and index evidence

Corpus passages remain unapproved until a qualified curator reviews them. The curator passage endpoint exposes checksums, inferred locator, extraction metadata and `review_revision`. Approval requires the current `expected_review_revision`; stale writes receive 409. Approval is not automatic, and OCR confidence is not legal confidence.

```sh
npm run corpus:index
# Explicit paid operation: at most 16 approved public passages in one batch.
npm run corpus:index -- --execute --max-batches 1
```

Only active, approved, fresh public India passages are embedded. Private Passport data is excluded. Old parse/source versions cannot enter retrieval after deactivation. Embedding model changes require a separate index; old vectors are not silently reused.

## 4. Request guidance

Restart the backend. Add `"allow_hosted_processing": true` to a guidance request only after the end user explicitly permits their question to be sent to the configured provider. The frontend consent flow is not yet wired; default API requests remain local. Without the flag, hosted calls do not occur.

Hosted prompts contain the authorized question, jurisdiction/date and retrieved public evidence—not the Passport, user identity or entire case. Questions can still contain personal/confidential information; minimize it and establish your privacy/retention policy before public use.

The service performs lexical/vector fusion, drafts cited claims, checks them in a separate model pass, and allows one repair. It mechanically checks source identity and currency before publication. Failed synthesis falls back to fresh exact excerpts. No matching approved evidence means no model-generated legal answer.

The semantic checker uses the configured model and is fallible; its pass state is **not independent legal verification**. Answers remain `REVIEW_REQUIRED`. Model responses cannot supply or alter authoritative URLs, dates or source quotations.

## Boundaries

- Exact vector search is bounded to 5000 eligible stored vectors; it is not pgvector/ANN or a proven large-scale search service.
- Provider calls are bounded but rate/budget controls must also be set on your provider account.
- Hindi translation, international corpus coverage and expert legal evaluations remain unvalidated. Hindi/non-India requests currently abstain.
- OpenAI requests set `store=false`; this alone is not a zero-retention guarantee. Gemini processing/retention must be assessed under its account terms.
- OCR is disabled by default. Docker includes Poppler/Tesseract English/Hindi; native OCR needs those binaries installed separately. Automatic OCR allows at most 20 low-text pages per document and rejects low-confidence output. Large scanned compilations require a reviewed batch workflow; no such compilation has been falsely marked fully parsed.

## Official transport references

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [Embeddings API](https://developers.openai.com/api/reference/resources/embeddings/methods/create).
- [Gemini generateContent API](https://ai.google.dev/api/generate-content) and [Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings).
- [Tesseract CLI and TSV output](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html).
