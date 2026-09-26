# Showcase readiness

## Sign in

Email verification is disabled by default (`REQUIRE_EMAIL_VERIFICATION=false`), as requested. Create an account at `/login`; the UI signs you in immediately. Existing unverified accounts can use their original password. Duplicate signup never changes an existing password in this mode. Email ownership is **not verified**; do not present it as verified identity. Password hashing, HttpOnly sessions, CSRF checks, rate limits and tenant boundaries remain enabled.

Password reset is hidden when SMTP is unavailable. It does not bypass password authentication. Configure SMTP before offering email recovery. Optional verified-email mode remains available by explicitly enabling the setting.

## What can be demonstrated

- Landing page, workspace and clearly labelled sample cases.
- Signup/login/logout and private saved cases.
- Product Passport entry and unresolved classification routing.
- Source-grounded questions, citations, evidence gaps and explicit hosted-AI consent.
- Safe source-only fallback when Groq is unavailable or rate-limited.

## Not complete — do not present as delivered

- Full expert-approved legal corpus, regulatory rules and legal accuracy benchmark.
- Complete live Passport round-trip/concurrent-save acceptance and fully operational human facilitator service.
- Complete international coverage, validated Hindi/legal translation and voice integrations.
- Live hosting, TLS/ingress acceptance, backup restore, load and independent penetration tests.
- Guaranteed live AI generation: the last external provider check returned HTTP 429. Source-only output is not a generated answer.

The project is an engineering prototype suitable for a scoped demonstration after rehearsal, not a fully completed production legal assistant. Use synthetic/public questions and identify mocked or unavailable features explicitly.

## GitGuardian notification follow-up

The notification references commit 434219b but does not identify file paths. That commit introduced literal test passwords in `backend/tests/test_accounts.py`; those are now generated randomly at runtime, as is the dummy password used for constant-time login checks. They were test values, not user login credentials. The exact incident links/paths are still needed to confirm all three findings. No suppression or history rewrite was performed. Historical findings require review/resolution in GitGuardian; real credentials, if identified, must be revoked/rotated rather than merely removed from source. Never paste secret values into chat.
