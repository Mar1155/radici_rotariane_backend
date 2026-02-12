# Radici Rotariane — Backend

Panoramica rapida della struttura del progetto e dei suoi componenti principali.

## Struttura essenziale

- `backend/` — Configurazione Django (settings, urls, asgi/wsgi) e middleware principali.
- `users/` — App utenti, modelli e logica di autenticazione.
- `chat/` — App realtime/Channels per messaggistica.
- `forum/` — App forum e contenuti.
- `section/` — App per sezioni/moduli del progetto.
- `scripts/` — Utility per dati demo.
- `manage.py` — Entry point Django.
- `requirements.txt` — Dipendenze runtime.
- `nixpacks.toml` — Build/deploy Railway (venv + pip).

## Script demo

Popola il database con dati di esempio:

```bash
python scripts/populate_demo.py
```

Opzioni:

```bash
python scripts/populate_demo.py clubs
python scripts/populate_demo.py skills
```

## Variabili d’ambiente (runtime)

Essenziali:
- `SECRET_KEY` — Chiave Django.
- `DEBUG` — `false` in produzione.
- `ALLOWED_HOSTS` — Lista separata da virgole (es. `example.com,api.example.com`).
- `DATABASE_URL` — Connessione Postgres (es. Railway).

Consigliate per produzione:
- `CORS_ALLOW_ALL_ORIGINS` — `false` in produzione (usa `CORS_ALLOWED_ORIGINS`).
- `CORS_ALLOWED_ORIGINS` — Lista separata da virgole.
- `CSRF_TRUSTED_ORIGINS` — Lista separata da virgole con schema (es. `https://example.com`).
- `LOG_LEVEL` — `INFO`/`DEBUG`.

Realtime (Channels):
- `REDIS_HOST` — Host Redis.
- `REDIS_PORT` — Porta Redis (default `6379`).

Media su S3 (se `USE_S3=true`):
- `USE_S3` — `true` per usare S3.
- `AWS_ACCESS_KEY_ID` — Access key.
- `AWS_SECRET_ACCESS_KEY` — Secret key.
- `AWS_STORAGE_BUCKET_NAME` — Nome bucket.
- `AWS_S3_REGION_NAME` — Regione (es. `us-east-1`).
- `AWS_S3_CUSTOM_DOMAIN` — (opzionale) CDN o custom domain.
- `AWS_S3_ADDRESSING_STYLE` — `virtual` o `path` (default `virtual`).

Opzionali:
- `LOG_FILE` — Path file log (default `app.log`).
- `STATIC_URL`, `STATIC_ROOT` — Static files (default `/static/`, `staticfiles`).
- `MEDIA_URL`, `MEDIA_ROOT` — Media files (default `/media/`, `media`).
- `DEEPL_API_KEY`, `DEEPL_API_URL` — Traduzioni.
- `GOOGLE_TRANSLATE_API_KEY`, `GOOGLE_TRANSLATE_API_URL` — Traduzioni.

Email (Gmail SMTP):
- `EMAIL_HOST` — Default `smtp.gmail.com`.
- `EMAIL_PORT` — Default `587`.
- `EMAIL_USE_TLS` — Default `true`.
- `EMAIL_HOST_USER` — Account Gmail.
- `EMAIL_HOST_PASSWORD` — App Password Gmail.
- `DEFAULT_FROM_EMAIL` — Mittente (default `EMAIL_HOST_USER`).
- `SUPPORT_EMAIL` — Email supporto (default `EMAIL_HOST_USER`).
- `SITE_NAME` — Nome visualizzato nelle email.

Reset password (OTP):
- `PASSWORD_RESET_OTP_TTL_MINUTES` — Default `30`.
- `PASSWORD_RESET_RESEND_SECONDS` — Default `60`.
- `PASSWORD_RESET_MAX_PER_HOUR` — Default `5`.
- `PASSWORD_RESET_MAX_ATTEMPTS` — Default `5`.

Verifica email (OTP):
- `EMAIL_VERIFICATION_OTP_TTL_MINUTES` — Default `30`.
- `EMAIL_VERIFICATION_RESEND_SECONDS` — Default `60`.
- `EMAIL_VERIFICATION_MAX_PER_HOUR` — Default `5`.
- `EMAIL_VERIFICATION_MAX_ATTEMPTS` — Default `5`.

## Componenti necessari

Per funzionare in produzione servono:
- **PostgreSQL** — Database principale (via `DATABASE_URL`).
- **Redis** — Backend per Django Channels (via `REDIS_HOST/REDIS_PORT`).
