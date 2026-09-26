# Hosting and account setup

## Showcase update

Email verification is now optional and defaults OFF per the project owner's request. Signup logs the user in immediately; existing unverified accounts remain accessible using their password. SMTP is not required for this mode, and password-reset UI stays hidden until SMTP is configured. Set `REQUIRE_EMAIL_VERIFICATION=true` to restore the verified-email flow described below. Unverified emails are not proof of ownership. See [current showcase status](SHOWCASE_STATUS.md); this update supersedes the mandatory-SMTP/verification statements below.

## Recommended first deployment

Use one paid Render Docker web service for the React build and FastAPI, managed PostgreSQL, managed Redis-compatible Key Value, and persistent storage for corpus files. Serving UI and API on the same HTTPS origin is required by the browser cookie implementation. A separate Vercel frontend is not the recommended configuration. Render's free web service has no persistent disks; do not use it for durable production corpus storage.

Primary documentation: https://render.com/docs/service-types, https://render.com/docs/disks, https://render.com/docs/free.

The existing alternative is a Linux server running `deploy/compose.yml`: Caddy terminates TLS, PostgreSQL stores accounts/cases, Redis shares rate limits, and a persistent volume holds corpus files. Hosting is not provisioned or paid for by this change.

## Required owner inputs

- Hosting account, region, budget, application domain and DNS access.
- Authenticated STARTTLS SMTP credentials (port 587) and verified sender; configure SPF/DKIM/DMARC with the email provider.
- A fresh Groq key with sufficient quota, entered only through the host's secret manager. Rotate the key previously shared in chat. Never use a `VITE_` environment variable for server credentials.
- Expert-approved source passages/rules, privacy/retention policy and operational owner.

## Deploy sequence

1. Build from repository root using `backend/Dockerfile`. Do not upload local databases, `.env`, `.dev-token` or `.mail-outbox`.
2. Configure variables from `deploy/production.env.example`. Use the exact public application origin for `PUBLIC_APP_URL` and `CORS_ORIGINS`; include its hostname in `ALLOWED_HOSTS` (and `127.0.0.1` for local health checks).
3. Configure PostgreSQL and Redis URLs using private connections and provider-required TLS. Set `APP_ENV=production`; never set `DEV_API_TOKEN`.
4. Run `alembic upgrade head` as a release/pre-deploy command before serving traffic. Current schema is 0005. Mount durable corpus storage at `/srv/data/corpus/raw`, writable by UID 10001.
5. Configure the ingress trust boundary before opening registration. The current image intentionally disables forwarded-header trust; without a trusted-proxy configuration all requests behind a proxy share an IP rate budget. Use only the verified ingress addresses with Uvicorn `--proxy-headers --forwarded-allow-ips=<trusted addresses>`; never blindly trust client-provided headers or `*` on a publicly reachable backend.
6. Check `/health/readiness`; perform real verification-mail delivery, sign-in, private case isolation, reset, logout and backup-restore tests over HTTPS.
7. Ingest/review official evidence. Production deliberately excludes source-text-only pilot approvals. Missing approved evidence must produce abstention, not invented legal answers.
8. Enable hosted mode only with explicit cloud-processing configuration and test a consented public question. Confirm `HOSTED_RAG`; a safe local fallback is not proof of successful generation.

## Account behaviour

`/login` provides signup, verification, sign-in, forgotten password and reset. Passwords are salted PBKDF2-HMAC-SHA256 (600,000 iterations). Opaque session values are stored only in HttpOnly cookies; database records hold their SHA-256 digests. Production cookies are Secure, SameSite=Strict and use the `__Host-` prefix. Sessions expire after 24 hours. Logout revokes the current session; reset revokes all sessions. Verification/reset tokens expire after 30 minutes and are single-use. Origin/CSRF checks and rate limits protect state-changing account endpoints. Built-in accounts cannot obtain staff roles; staff identity/MFA integration needs separate acceptance before enabling staff workflows.

Development without SMTP writes messages to ignored, owner-only `backend/.mail-outbox/` files. Open the latest file locally and follow its link; do not share its token. No real email is sent in this mode. Set PUBLIC_APP_URL to the origin you actually use and restart the backend if necessary. Production refuses to start without SMTP configuration.

## Release gates still open

This is a hardened pilot, not a security certification or a complete legal product. Independent penetration/accessibility/load testing, trusted proxy setup, monitored email delivery, encrypted backup restore, retention/deletion review, complete live Passport round-trip, expert legal/bilingual validation and broader corpus coverage remain mandatory. Docker runtime/public TLS have not been tested here. Groq last returned HTTP 429; provider quota must be resolved before promising live generation.
