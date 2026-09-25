# Module A — frontend delivery status
Updated: 22 September 2026

## Delivered scope
The core Module A journey is implemented in React and JavaScript against **explicitly labelled, local mock APIs**. This is a frontend demonstration, not a production legal service. No backend or real legal decisions are connected. Reload resets cases; only the interface language is stored locally.

### Implemented
- Warm-black, gold and ivory landing/workspace; top navigation, responsive layouts, lazy-loaded globe, pause/reduced-motion controls.
- Guest onboarding with explicit session notice; separate jurisdiction, date and language controls.
- Six-step Passport: intended use, claims, administration, food subroute, authoritative reference, ingredients, origin, processing, evidence, applicant, stage, markets and disclosures. Research skips claims; cosmetic administration options are narrowed.
- Structured ingredient editor with biological type, part, origin, sourcing and explicit Unknown values; up to 20 ingredients without secret ratios.
- Local evidence-file metadata checks: PDF/TXT, 5 MB limit. File contents are not uploaded or read.
- Fact confirmation; independent unresolved regulatory/IP/ABS displays; context changes invalidate results, confirmation and sharing.
- Nine-section mock guidance with progress, cancellation, retry, timeout, partial results, conflicting/missing evidence, restricted-source and translation-unavailable examples.
- Citation inspection retains original synthetic passages and all traceability fields. Fictional sources are never presented as real law.
- General-question journey bypasses Passport.
- Consented mock reviewer queue, synthetic comments, withdrawal and cancellation on context changes.
- Case checklist, JSON/HTML/browser-PDF actions, history, snapshot downloads, archive/restore and session deletion.
- English/Hindi UI copy and wizard options; switching language preserves the wizard step and stored option values. Original user/source data and technical identifiers remain unchanged.
- Native modal keyboard dismissal, labelled controls, visible focus and mobile layout rules.

## Verification completed
- Production build passed.
- ESLint passed.
- 24 domain, API-contract, mock-stream and Passport-rule tests passed.
- Browser-tested synthetic case creation, food branch, ingredient save, language switching and step preservation, fact confirmation, guidance, citation dialog/Escape, mock handoff/reviewer response, archive/restore and jurisdiction invalidation.
- Checked workspace at a 390 px viewport: no document-level horizontal overflow. Export cards stack vertically.
- No runtime error was observed during the exercised browser flow. Deprecated Three.js clock removed.

## Deliberate backend boundaries
Modules B/C/D must supply actual authentication, durable secure storage, authoritative legal rules/retrieval, evidence verification, document ingestion, source permissions, real facilitator delivery and server-enforced consent. Do not use the mock app for confidential or real legal decisions.
BHASHINI voice and validated translation/normalization await their service integration. Jurisdiction comparison must wait for validated answer sets. PWA/offline caching is not implemented; never cache case secrets by default.

## Release review still needed
Independent Hindi/domain review, full assistive-technology audit, wider browser/device testing, low-end 3D performance testing and integrated backend acceptance testing. These are not represented as passed. The build retains a bundle-size advisory for the application/Three.js chunks.

## Run checks
```sh
npm run dev -- --host 127.0.0.1
npm run build
npm run lint
node --test src/domain.test.js src/api.test.js src/mockApi.test.js src/passportRules.test.js
```
