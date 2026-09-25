# IP-SAKTI Sahayak — Naut IQ
Module A for SIH 26045. React + JavaScript (JSX), Vite, CSS and Three.js.

## Run locally
```sh
npm ci
npm run dev -- --host 127.0.0.1
```

## Verify
```sh
npm run build
npm run lint
node --test src/domain.test.js src/api.test.js src/mockApi.test.js src/passportRules.test.js
```

See [MODULE_A_STATUS.md](MODULE_A_STATUS.md) for implemented journeys, browser checks and remaining production integration.

## Mock-first architecture
- `src/App.jsx`: top-navigation shell and routes.
- `src/Landing.jsx`: landing experience.
- `src/Passport.jsx`, `passportRules.js`, `IngredientEditor.jsx`: conditional product facts.
- `src/mockApi.js`: synthetic streaming guidance and local reviewer adapter.
- `src/MockGuidance.jsx`, `MockQuestion.jsx`, `MockReview.jsx`: mock request UI.
- `src/CaseHistory.jsx`: history, snapshots and archive/restore.
- `src/Localized.jsx`, `uiHindi.js`: declared UI text localization; original data is preserved.
- `src/state.jsx`, `context.js`: in-memory session state.
- `src/domain.js`: invalidation and escaped exports.
- `src/api.js`: proposed schema-validated real API adapter, not connected.

All cases reset on reload. Use synthetic data only. Only the language preference is persisted locally. Google Fonts and user-opened official links remain external requests; mock questions are not sent to an AI provider. File selection validates metadata only.

Backend authentication, secure persistence, reviewed legal rules and retrieval, real source verification and facilitator delivery belong to Modules B/C/D. Optional voice/offline features and independent accessibility/language audits remain before a production release.

Information, not legal advice.
