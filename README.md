# Tapstar

AI-powered Google review SaaS for Indian local businesses. Customers scan a QR, pick a rating + what they experienced, and Tapstar writes the review for them in Hinglish, Hindi, Marathi, English, or Devanagari-script Hinglish. Low-rating customers are diverted to a private feedback inbox so bad reviews never reach Google.

## Highlights

- **Per-business-type prompt tuning** — 68 Indian-market business types across 12 industry groups. A hardware store's review mentions stock/pricing/delivery; a clinic's review mentions doctor/wait time/fees.
- **Language support** — English, Hinglish (Roman + देवनागरी), Hindi (हिंदी), Marathi (मराठी), Minglish, Random.
- **Always-positive output** — forbidden-phrase filter blocks complaints, caveats, and backhanded compliments like "had to wait", "for the area", "not the best but".
- **Private negative filter** — configurable threshold (default ≤ 2 stars) routes unhappy customers to a private inbox instead of Google.
- **5 print-ready QR templates** — A5 standee, A4 poster, A4 table tent, A6 counter card, A4 6-up sticker sheet. Preview or download as PDF.
- **Place ID forgiveness** — accepts raw Place IDs, full Google Maps URLs, `writereview` links, and short `maps.app.goo.gl` / `g.page` URLs (resolved server-side).
- **Multi-location** — Starter: 1 location. Business: 5 locations. Each gets its own QR + review URL.
- **Subscription billing** — Easebuzz (UPI + cards + net banking, INR).

## Stack

Django 5 · DRF · PostgreSQL (SQLite in dev) · Anthropic Claude · qrcode + Pillow · ReportLab · Easebuzz · Celery + Redis · HTMX · WhiteNoise · Gunicorn · Nginx.

## Local development

```bash
# 1. Python 3.12 + virtualenv
python -m venv venv
source venv/Scripts/activate      # Git Bash / MSYS on Windows
# source venv/bin/activate        # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# At minimum set SECRET_KEY. DATABASE_URL is optional (SQLite fallback).

# 4. Database
python manage.py migrate
python manage.py createsuperuser

# 5. Run
python manage.py runserver
```

Visit:

| URL | Purpose |
|-----|---------|
| `/` | Public landing page |
| `/auth/signup/` | Create an owner account |
| `/dashboard/` | Business dashboard (after onboarding) |
| `/settings/` | Language / tone / business category / categories / keywords |
| `/feedback/` | Private negative-feedback inbox |
| `/admin/` | Django admin |
| `/r/<qr_token>/` | Customer-facing QR review page (public) |

### With AI enabled

Set `ANTHROPIC_API_KEY` in `.env` to activate the Claude-powered review generator. Without a key the system serves pre-written fallback variants (still fully functional, just not AI-generated).

## Apps

| App | Responsibility |
|-----|----------------|
| `accounts` | Custom User with subscription fields + auth views |
| `businesses` | Business + Location models, QR code generation, dashboard, print templates |
| `settings_mgr` | Per-business language/tone/category/menu config (+ per-location overrides) |
| `reviews` | Business-type registry, AI prompt + generation, variants, submission tracking |
| `feedback` | Private negative-review inbox |
| `analytics` | Daily aggregation, dashboard charts |

## Configuration

All configuration is via environment variables — see [`.env.example`](./.env.example) for the full list. Key groups:

- **Django core** — `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL`
- **Database** — `DATABASE_URL` (SQLite fallback when blank)
- **HTTPS / security** — `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, cookie-secure flags
- **Integrations** — `ANTHROPIC_API_KEY`, `GOOGLE_PLACES_API_KEY`, `EASEBUZZ_*`, SMTP settings
- **Logging** — `LOG_LEVEL`, optional `LOG_DIR` for rotating file logs

## Deployment

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for a step-by-step Ubuntu + Gunicorn + Nginx guide (covers Postgres, Redis, Let's Encrypt, systemd units, and the deploy/upgrade checklist).

## Project layout

```
tapstar_project/   Django settings + root URLs + wsgi/asgi
accounts/          Custom User, auth, subscription, payment flows
businesses/        Business, Location, QR generation, print PDFs
reviews/           business_types.py registry, ai.py prompt, fallback.py
settings_mgr/      Business & Location configuration overrides
feedback/          Private feedback inbox
analytics/         Event aggregation + charts
templates/         All server-rendered pages
```

## License

Proprietary — © 1TechSpace.
