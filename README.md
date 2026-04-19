# Tapstar

AI-powered Google review SaaS for Indian local businesses — QR code to multilingual AI-generated review, with private feedback filtering for low-rating customers.

## Stack

Django 5 · DRF · PostgreSQL (or SQLite in dev) · Anthropic Claude · qrcode + Pillow · ReportLab · Easebuzz (payments) · Celery + Redis · HTMX.

## Quickstart

```bash
# 1. Create a virtualenv
python -m venv venv
source venv/Scripts/activate   # Windows bash
# source venv/bin/activate     # macOS/Linux

# 2. Install deps
pip install -r requirements.txt

# 3. Configure env
cp .env.example .env
# Fill SECRET_KEY at minimum. DATABASE_URL optional (SQLite fallback).

# 4. Migrate + create superuser
python manage.py migrate
python manage.py createsuperuser

# 5. Run
python manage.py runserver
```

Visit:

- `/` — landing
- `/auth/signup/` — create an account
- `/dashboard/` — business dashboard (after onboarding)
- `/admin/` — Django admin
- `/r/<qr_token>/` — customer QR review page

## Apps

| App | Responsibility |
|-----|----------------|
| `accounts` | Custom User model with subscription + Razorpay fields |
| `businesses` | Business + Location models, QR code generation, dashboard |
| `settings_mgr` | Per-business language/tone/keywords/menu config |
| `reviews` | AI generation, variants, submission tracking |
| `feedback` | Private negative-review inbox |
| `analytics` | Daily aggregation, dashboard charts |

## Sprint 1 (shipped)

- [x] Django project + 6 apps
- [x] All models + admin
- [x] Custom User with subscription fields
- [x] Business registration + first Location auto-created
- [x] QR PNG generated on Location save (signal)
- [x] Dashboard home with QR preview + download
- [x] Customer review page placeholder at `/r/<token>/`

## Sprint 2 (next)

Customer review page full flow: rating → categories → items → AI generation → 4 variants → edit → submit to Google. See `tapstar_claude_code_prompt.md`.

## Env vars

See `.env.example` — all configuration is via environment variables.
