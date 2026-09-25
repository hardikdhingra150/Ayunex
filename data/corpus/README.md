# Authoritative corpus — scope and access policy

`catalog.json` is an explicit allowlist, not a web crawler. `ingestion-report.json` records actual success/failure. `raw/<sha256>.pdf` preserves source bytes. Database tables preserve immutable document versions, PDF page locators, passage hashes and review events.

## Acquired in this pass

Five indexed PDFs / 161 pages, all **pending review**. On 25 September, structural reparsing produced **553 active segments**, preserving the original **338 segments as inactive history**. One oversize active segment is quarantined; zero passages are legally approved. `ingestion-report.json` retains original acquisition counts, not a live parsing inventory.

- Patents Act 1970, official consolidation through 1 August 2024 — 69 pages.
- Patents Amendment Rules 2024 — 40 pages.
- Patents Second Amendment Rules 2024 — 9 pages.
- NBA ABS Regulations 2025 — 28 pages.
- NBA classification of biological resources, derivatives and value-added products — 15 pages.

The FSSAI 2022 notification URL returned non-PDF content and was rejected. The FSSAI 2025 Ayurveda Aahara order was downloaded but **not indexed**: its insufficient machine-readable page coverage requires OCR/manual review. Raw acquisition is not counted as usable evidence. These failed attempts are recorded in `ingestion-report.json`.

The India Code Biological Diversity Act download timed out. India Code's previous home page announces migration to [indiacode.gov.in](https://www.indiacode.nic.in/); its migrated site was not reachable during this run. No replacement text or claimed import was invented.

The [TKDL home page](https://www.tkdl.res.in/) limits full database access to patent offices under access agreements. It is therefore a restricted pointer only. IP India's search registries are manual official links; no CAPTCHA bypass, restricted subscription, personal-data harvest or bulk registry scraping is implemented.

## Source evidence

- [IP India Acts](https://ipindia.gov.in/pages/patents/publications/acts)
- [IP India Rules](https://ipindia.gov.in/pages/patents/publications/rules)
- [NBA notifications and guidelines](https://www.nbaindia.nic.in/public-information/notification-guidelines)

The original PS's `nbaindia.or` is incomplete. Official NBA sources are catalogued using the confirmed NBA domains.

## Synchronize

```sh
npm run backend:migrate
npm run corpus:sync
# Retry one catalog item without overwriting other report entries:
npm run corpus:sync -- --source biodiversity-act
```

Downloads enforce HTTPS/authority allowlists, reject private DNS targets, check robots policy, bound redirects/download size and reject HTML login/challenge responses. PDF extraction is a subprocess with CPU/page/text/time budgets. Deployment egress rules should additionally enforce the domain/IP restrictions at the network boundary.

## Review before use

1. Search with `reviewed_only=false` for research or curator inspection. Results are explicitly unreviewed.
2. A verified curator checks the original PDF, exact provision, extraction fidelity, amendments, effective interval and current applicability.
3. Record a hash-bound approval through `PATCH /api/v1/corpus/passages/{id}/review`, including provision, validity dates, review-expiry date and notes.
4. Only active, approved, effective and fresh passages enter the extractive guidance adapter. A new source version requires new review.

`GUIDANCE_MODE=corpus` returns original reviewed excerpts, **not generated product-specific legal advice**. It returns `MISSING_EVIDENCE` when none qualify. This is a useful safe retrieval baseline, not the complete evaluated multilingual RAG system.

## Coverage still needed

This is a seed corpus, not the complete dataset. India Code retrieval, the Biological Diversity Act and 2024/2025 Rules, AYUSH/drug/food/cosmetic/advertising regimes, GI/trademark/design/copyright/plant-variety law, authoritative texts, case law and international regimes need further acquisition and expert review. The NBA FAQ also describes later biodiversity-rule amendments; never assume a 2024-only corpus is current.

Raw PDFs are reproducible downloads and excluded from Git. Do not publicly redistribute a corpus without checking source terms. Acquisition dates are never substituted for legal effective dates.
