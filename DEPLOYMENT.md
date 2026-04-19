# Tapstar — Deployment Guide

Production deployment on Ubuntu 22.04 LTS behind nginx, served by gunicorn, with PostgreSQL and Redis. Examples target the domain **`tapstart.1techspace.in`** — substitute if yours differs.

The guide assumes:

- A fresh Ubuntu 22.04 server reachable by SSH as a sudo-enabled user.
- An A record for `tapstart.1techspace.in` pointing at the server's public IP.
- Port 80 and 443 open to the internet.

Everything below is copy-paste ready. Lines prefixed `#` are comments or expected output. Commands run as your sudo user unless noted.

---

## 0. Architecture

```
 Internet  ─►  nginx (80/443, TLS)  ─►  gunicorn (unix socket)  ─►  Django (tapstar)
                     │
                     ├── /static/  → /var/www/tapstar/staticfiles
                     └── /media/   → /var/www/tapstar/media

 systemd: tapstar-web.service       (gunicorn)
 systemd: tapstar-celery.service    (celery worker — optional)
 Postgres 16 on 127.0.0.1:5432
 Redis 7   on 127.0.0.1:6379
```

---

## 1. Install system packages

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  python3.12 python3.12-venv python3-pip python3-dev \
  build-essential libpq-dev \
  postgresql postgresql-contrib \
  redis-server \
  nginx \
  git ufw \
  certbot python3-certbot-nginx
```

> **Note on Python 3.12** — Ubuntu 22.04 ships 3.10 by default. If 3.12 isn't available from apt, either install via `deadsnakes` PPA or use 3.10 (the project is compatible with 3.10+). Just keep the version consistent between local dev and prod.

---

## 2. Create an app user + directories

Run the Django service as an unprivileged user so a compromise of the app can't touch the rest of the system.

```bash
sudo useradd --system --create-home --shell /bin/bash tapstar

sudo mkdir -p /var/www/tapstar/{staticfiles,media}
sudo mkdir -p /var/log/tapstar
sudo mkdir -p /etc/tapstar
sudo mkdir -p /run/tapstar

sudo chown -R tapstar:tapstar /var/www/tapstar /var/log/tapstar /run/tapstar
sudo chown -R root:tapstar /etc/tapstar
sudo chmod 750 /etc/tapstar
```

---

## 3. PostgreSQL — database + user

```bash
sudo -u postgres psql <<'SQL'
CREATE USER tapstar WITH PASSWORD 'REPLACE_WITH_STRONG_PASSWORD';
CREATE DATABASE tapstar OWNER tapstar;
ALTER ROLE tapstar SET client_encoding TO 'utf8';
ALTER ROLE tapstar SET default_transaction_isolation TO 'read committed';
ALTER ROLE tapstar SET timezone TO 'Asia/Kolkata';
\q
SQL
```

Verify:

```bash
PGPASSWORD=REPLACE_WITH_STRONG_PASSWORD psql -h 127.0.0.1 -U tapstar -d tapstar -c '\l'
```

---

## 4. Redis

Already installed above. Confirm it's listening on loopback only (default on Ubuntu):

```bash
sudo systemctl enable --now redis-server
redis-cli ping
# PONG
```

No extra config needed for single-host deployment.

---

## 5. Clone the code

```bash
sudo -u tapstar -H bash <<'BASH'
cd ~
git clone https://github.com/ChetanR01/TapStar.git app
cd app
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
BASH
```

The project is now at `/home/tapstar/app` with an isolated venv at `/home/tapstar/app/venv`.

---

## 6. Environment file

Create `/etc/tapstar/tapstar.env` (root-owned, readable by the `tapstar` group so the systemd service can read it):

```bash
sudo tee /etc/tapstar/tapstar.env >/dev/null <<'ENV'
# --- Django core ---
SECRET_KEY=PASTE_A_LONG_RANDOM_STRING_HERE
DEBUG=False
ALLOWED_HOSTS=tapstart.1techspace.in
CSRF_TRUSTED_ORIGINS=https://tapstart.1techspace.in
SITE_URL=https://tapstart.1techspace.in

# --- Database ---
DATABASE_URL=postgres://tapstar:REPLACE_WITH_STRONG_PASSWORD@127.0.0.1:5432/tapstar

# --- Media ---
MEDIA_ROOT=/var/www/tapstar/media

# --- HTTPS (start disabled; flip on after certbot in step 12) ---
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False

# --- Logging ---
LOG_LEVEL=INFO
LOG_DIR=/var/log/tapstar

# --- Redis / Celery ---
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_TASK_ALWAYS_EAGER=False

# --- Anthropic ---
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# --- Google Places (optional) ---
GOOGLE_PLACES_API_KEY=

# --- Easebuzz ---
EASEBUZZ_KEY=
EASEBUZZ_SALT=
EASEBUZZ_ENV=prod

# --- Email ---
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=you@example.com
EMAIL_HOST_PASSWORD=app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Tapstar <noreply@tapstart.1techspace.in>
ENV

sudo chown root:tapstar /etc/tapstar/tapstar.env
sudo chmod 640 /etc/tapstar/tapstar.env
```

Generate a new `SECRET_KEY`:

```bash
sudo -u tapstar /home/tapstar/app/venv/bin/python -c \
  "import secrets; print(secrets.token_urlsafe(64))"
```

Paste the output into `SECURE_KEY=` above (`sudo nano /etc/tapstar/tapstar.env`).

---

## 7. First-time Django setup

```bash
sudo -u tapstar -H bash <<'BASH'
cd /home/tapstar/app
set -a
source /etc/tapstar/tapstar.env
set +a
source venv/bin/activate

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser
BASH
```

Point `STATIC_ROOT` to the web-facing location so nginx can serve static files without going through Django:

```bash
sudo -u tapstar ln -sf /home/tapstar/app/staticfiles /var/www/tapstar/staticfiles
```

(The project already writes to `<project>/staticfiles` by default. If you prefer to write directly to `/var/www/tapstar/staticfiles`, set `STATIC_ROOT` in settings or add an env var — both approaches work.)

Make sure `MEDIA_ROOT` is writable by the `tapstar` user (it's already owned by them from step 2).

---

## 8. Gunicorn — systemd service

Create `/etc/systemd/system/tapstar-web.service`:

```ini
[Unit]
Description=Tapstar gunicorn (web)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=tapstar
Group=tapstar
RuntimeDirectory=tapstar
WorkingDirectory=/home/tapstar/app
EnvironmentFile=/etc/tapstar/tapstar.env
ExecStart=/home/tapstar/app/venv/bin/gunicorn tapstar_project.wsgi:application \
    --workers 3 \
    --threads 2 \
    --bind unix:/run/tapstar/gunicorn.sock \
    --access-logfile /var/log/tapstar/gunicorn-access.log \
    --error-logfile  /var/log/tapstar/gunicorn-error.log \
    --capture-output \
    --timeout 60
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/tapstar/app /var/www/tapstar /var/log/tapstar /run/tapstar

[Install]
WantedBy=multi-user.target
```

> **Worker count**: 3 workers × 2 threads handles a small VPS well. Scale up as traffic grows (`2 × CPU_cores + 1` is a good rule for pure Django).

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tapstar-web
sudo systemctl status tapstar-web   # should be "active (running)"
```

If it crashes, check `sudo journalctl -u tapstar-web -n 80` and `/var/log/tapstar/gunicorn-error.log`.

---

## 9. Celery worker — optional

Only needed if you want background tasks (currently the project runs them eagerly unless `CELERY_TASK_ALWAYS_EAGER=False`).

Create `/etc/systemd/system/tapstar-celery.service`:

```ini
[Unit]
Description=Tapstar celery worker
After=network.target redis-server.service postgresql.service
Requires=redis-server.service postgresql.service

[Service]
Type=simple
User=tapstar
Group=tapstar
WorkingDirectory=/home/tapstar/app
EnvironmentFile=/etc/tapstar/tapstar.env
ExecStart=/home/tapstar/app/venv/bin/celery -A tapstar_project worker \
    --loglevel=INFO \
    --logfile=/var/log/tapstar/celery.log
Restart=on-failure
RestartSec=5

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/tapstar/app /var/www/tapstar /var/log/tapstar

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tapstar-celery
```

---

## 10. Nginx site

Create `/etc/nginx/sites-available/tapstar`:

```nginx
upstream tapstar_app {
    server unix:/run/tapstar/gunicorn.sock fail_timeout=0;
}

# HTTP — ACME challenge + redirect to HTTPS (certbot will rewrite this
# block after it issues the cert; fine to leave as-is for the first run)
server {
    listen 80;
    listen [::]:80;
    server_name tapstart.1techspace.in;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS — main site
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name tapstart.1techspace.in;

    client_max_body_size 16M;

    # These two lines are filled in by certbot in step 12.
    # ssl_certificate     /etc/letsencrypt/live/tapstart.1techspace.in/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/tapstart.1techspace.in/privkey.pem;
    # include /etc/letsencrypt/options-ssl-nginx.conf;
    # ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers (HSTS handled by Django)
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "same-origin" always;

    # Static assets — served directly by nginx, long cache
    location /static/ {
        alias /home/tapstar/app/staticfiles/;
        access_log off;
        expires 30d;
        add_header Cache-Control "public";
    }

    # User-uploaded media (logos, QR PNGs, etc.)
    location /media/ {
        alias /var/www/tapstar/media/;
        access_log off;
        expires 7d;
    }

    # Everything else → Django
    location / {
        proxy_pass http://tapstar_app;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host  $host;
        proxy_redirect   off;
        proxy_read_timeout 60s;
    }

    # Deny hidden files (.git, .env, etc.)
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

Enable:

```bash
sudo ln -sf /etc/nginx/sites-available/tapstar /etc/nginx/sites-enabled/tapstar
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 11. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'     # 80 + 443
sudo ufw enable
sudo ufw status
```

---

## 12. TLS with Let's Encrypt

Before running certbot, make sure:
- `http://tapstart.1techspace.in` resolves to this server (`dig +short tapstart.1techspace.in`).
- Port 80 reaches the box.

```bash
sudo certbot --nginx -d tapstart.1techspace.in \
  --redirect \
  --agree-tos \
  -m you@example.com \
  --non-interactive
```

Certbot edits `/etc/nginx/sites-available/tapstar` in place — uncommenting the `ssl_certificate*` and `ssl_*` lines and setting up auto-renewal via a systemd timer.

Confirm:

```bash
sudo systemctl list-timers | grep certbot
sudo certbot renew --dry-run
```

---

## 13. Turn on HTTPS enforcement inside Django

Now that TLS is live, open `/etc/tapstar/tapstar.env` and flip the security flags to True:

```bash
sudo sed -i 's/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=True/' /etc/tapstar/tapstar.env
sudo sed -i 's/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=True/' /etc/tapstar/tapstar.env
sudo sed -i 's/^CSRF_COOKIE_SECURE=.*/CSRF_COOKIE_SECURE=True/' /etc/tapstar/tapstar.env
sudo sed -i 's/^SECURE_HSTS_SECONDS=.*/SECURE_HSTS_SECONDS=3600/' /etc/tapstar/tapstar.env

sudo systemctl restart tapstar-web
```

Verify HTTPS works end-to-end, then raise HSTS and enable subdomain coverage:

```bash
sudo sed -i 's/^SECURE_HSTS_SECONDS=.*/SECURE_HSTS_SECONDS=31536000/' /etc/tapstar/tapstar.env
sudo sed -i 's/^SECURE_HSTS_INCLUDE_SUBDOMAINS=.*/SECURE_HSTS_INCLUDE_SUBDOMAINS=True/' /etc/tapstar/tapstar.env
sudo sed -i 's/^SECURE_HSTS_PRELOAD=.*/SECURE_HSTS_PRELOAD=True/' /etc/tapstar/tapstar.env

sudo systemctl restart tapstar-web
```

> Only enable HSTS preload once you're committed — browsers will refuse plain HTTP to this domain for a year.

---

## 14. Log rotation

Systemd journal handles stdout/stderr. For gunicorn's own log files plus optional `LOG_DIR`, drop a logrotate config:

```bash
sudo tee /etc/logrotate.d/tapstar >/dev/null <<'LR'
/var/log/tapstar/*.log {
    weekly
    missingok
    rotate 10
    compress
    delaycompress
    notifempty
    copytruncate
    su tapstar tapstar
}
LR
```

---

## 15. Smoke test

From your laptop:

```bash
curl -I https://tapstart.1techspace.in/
# HTTP/2 200
# content-type: text/html; charset=utf-8
```

Browse to:

- `https://tapstart.1techspace.in/` — landing
- `https://tapstart.1techspace.in/auth/signup/` — create the first real owner
- `https://tapstart.1techspace.in/admin/` — log in with the superuser from step 7

Django sanity check:

```bash
sudo -u tapstar -H bash <<'BASH'
cd /home/tapstar/app
set -a; source /etc/tapstar/tapstar.env; set +a
source venv/bin/activate
python manage.py check --deploy
BASH
```

(Some "insecure" warnings are OK if you intentionally kept a flag low — e.g. HSTS=3600 while verifying.)

---

## 16. Deploy / upgrade checklist

When shipping new code:

```bash
sudo -u tapstar -H bash <<'BASH'
cd /home/tapstar/app
git fetch origin
git checkout main
git pull --ff-only

source venv/bin/activate
pip install -r requirements.txt

set -a; source /etc/tapstar/tapstar.env; set +a
python manage.py migrate --noinput
python manage.py collectstatic --noinput
BASH

sudo systemctl restart tapstar-web
sudo systemctl restart tapstar-celery     # if the worker is enabled
```

If migrations take a while, consider running them before `restart` so gunicorn serves the old code with the new schema during the window, then restart.

### Rollback

```bash
sudo -u tapstar -H bash <<'BASH'
cd /home/tapstar/app
git log --oneline -n 10   # find the previous good commit
git checkout <sha>
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput    # see note below
BASH
sudo systemctl restart tapstar-web
```

Django migrations aren't always forward+backward compatible. If a rollback would drop a column or table, you need either a data-preserving manual migration or a restore from backup. Test important migrations on a staging copy first.

---

## 17. Backups

At minimum, take nightly Postgres dumps:

```bash
sudo tee /etc/cron.daily/tapstar-backup >/dev/null <<'SH'
#!/bin/bash
set -euo pipefail
DEST=/var/backups/tapstar
mkdir -p "$DEST"
DATE=$(date +%F)
PGPASSWORD=REPLACE_WITH_STRONG_PASSWORD pg_dump -h 127.0.0.1 -U tapstar tapstar \
  | gzip > "$DEST/tapstar-$DATE.sql.gz"
find "$DEST" -name 'tapstar-*.sql.gz' -mtime +30 -delete
SH
sudo chmod +x /etc/cron.daily/tapstar-backup
```

For media (logos, QRs), either rsync `/var/www/tapstar/media` to object storage nightly or snapshot the disk.

---

## 18. Common issues

| Symptom | Likely cause |
|---------|--------------|
| `502 Bad Gateway` | gunicorn isn't running or socket path wrong — check `sudo systemctl status tapstar-web` |
| `CSRF verification failed` on POST | `CSRF_TRUSTED_ORIGINS` missing `https://tapstart.1techspace.in` |
| `DisallowedHost` | `ALLOWED_HOSTS` doesn't include the domain you hit |
| Infinite HTTPS redirect | `SECURE_PROXY_SSL_HEADER` is fine, but nginx must send `X-Forwarded-Proto https` — it does in the config above |
| Static files 404 | `collectstatic` not run, or nginx `alias` path wrong |
| Uploaded images 403 | `/var/www/tapstar/media` not owned by `tapstar:tapstar` or readable by nginx |
| Permission denied on socket | `RuntimeDirectory=tapstar` missing, or nginx runs as a user that can't read `/run/tapstar/gunicorn.sock` |

### Useful commands

```bash
sudo systemctl status tapstar-web
sudo journalctl -u tapstar-web -f
sudo tail -f /var/log/tapstar/gunicorn-error.log
sudo tail -f /var/log/nginx/error.log
sudo -u tapstar /home/tapstar/app/venv/bin/python /home/tapstar/app/manage.py check --deploy
```

---

## 19. What's next

- Enable Google Places API and set `GOOGLE_PLACES_API_KEY` to get cover images on the customer review page when an owner has a Place ID but no uploaded logo.
- Configure Easebuzz production keys (`EASEBUZZ_ENV=prod`) before accepting live payments.
- Wire up a real email backend (SendGrid / Mailgun / SES) — the console backend won't deliver mail in production.
- Point a monitoring probe (UptimeRobot, BetterStack, etc.) at `https://tapstart.1techspace.in/` and the admin login page.
