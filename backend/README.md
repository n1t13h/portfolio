# Portfolio backend

FastAPI service for the photography portfolio. It serves published photos and collections to the
site, and gives one admin (password + TOTP 2FA) the tools to curate them. Photos live in
Cloudflare R2; metadata lives in SQLite.

Design: [`../docs/superpowers/specs/2026-10-22-backend-design.md`](../docs/superpowers/specs/2026-10-22-backend-design.md)
· Plan: [`../docs/superpowers/plans/2026-10-22-backend.md`](../docs/superpowers/plans/2026-10-22-backend.md)

## How it is organised

```
app/
  main.py            app factory: wires settings, storage, clock, notifier, Unsplash client
  core/              config, database, clock, security helpers, domain errors
  models/            one SQLAlchemy table per file
  integrations/      the outside world behind small interfaces: storage (R2), unsplash, notifier (Telegram)
  services/          all business logic; no HTTP in here
  api/public/        read-only routes + contact form (no login)
  api/admin/         everything under /a/<ADMIN_PATH_PREFIX>, behind login + 2FA
  cli.py             create-admin, reset-admin, sync, seed, backup, notify-pending
alembic/versions/    database migrations
deploy/              Caddy + systemd files
tests/               fakes.py has in-memory stand-ins for R2, Unsplash, Telegram and the clock
```

Rules that keep it maintainable: routers stay thin and call services; services reach R2, Unsplash
and Telegram only through the interfaces in `integrations/` (so tests never touch the network);
all configuration comes from `app/core/config.py`; files stay small and single-purpose.

## Run it locally with Docker

```bash
docker compose up --build -d          # API on :8000 (docs at /docs), S3-compatible store on :9090
uv run python scripts/smoke_local.py  # end-to-end check: 2FA login, upload, publish, read back
docker compose down                   # add -v to also wipe the local database and photos
```

The compose file runs the API in the same image you would deploy, with Adobe's S3Mock standing in for
R2 (it does not check signatures or enforce CORS, so it proves the flow, not R2's specifics).
Local admin path: `/a/local-admin-path-0123456789`. Create your own admin with
`docker compose exec api python -m app.cli reset-admin <name>` (it prompts for a password).
The smoke script resets the local admin on every run.
To try the real integrations, export `UNSPLASH_ACCESS_KEY` / `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`
before `docker compose up`.

## Develop

```bash
cp .env.example .env        # fill in ADMIN_PATH_PREFIX, SESSION_SECRET, CDN_BASE_URL at minimum
uv sync
uv run alembic upgrade head
uv run python -m app.cli create-admin <username>     # prints the 2FA QR URI + recovery codes
uv run uvicorn app.main:create_app --factory --reload   # DEBUG=true also serves /docs
```

Quality gates (all must pass before a change is done):

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy app tests
```

Tests use fakes and an in-memory database; none of them need network access or credentials.
Changing a model without a migration fails `test_migrations_have_no_drift_from_the_models`;
create one with `uv run alembic revision --autogenerate -m "what changed" --rev-id 000N`.
Adding a setting without documenting it in `.env.example` fails `test_env_example_documents_every_setting`.

## API at a glance

Request bodies over 1 MB get a 413 (photos go straight to R2, never through the API).

Public (cached at the edge: `Cache-Control: public, max-age=300` + `ETag`):

| Route | Returns |
|---|---|
| `GET /photos` | published photos in the admin's order |
| `GET /collections` | published collections in the admin's order, with covers |
| `GET /collections/{slug}` | one collection: chapters, photos, covers |
| `GET /photos/{id}/download` | 302 to a short-lived link, only if the admin enabled downloads for that photo |
| `POST /contact` | stores a message and notifies the owner on Telegram |
| `GET /health` | liveness |

A photo is public only if it is published and not inside a draft collection.

Admin (`/a/<ADMIN_PATH_PREFIX>/…`; log in at `auth/login` with password and a 6-digit code or a
recovery code; every non-GET call needs the header `X-CSRF: 1`): `photos` (upload ticket → browser
PUTs to R2 → `confirm`, edit, publish, `allow-download`, delete, `order`), `collections`,
`chapters`, and `sync` (start, full resync, status). Open `/docs` with `DEBUG=true` for the full list.

## Operating it

**Unsplash sync** (`python -m app.cli sync`, monthly via timer, or the admin button): imports only
photos it has not seen, as drafts. It stops at the first photo it already has, remembers anything it
could not finish, and respects Unsplash's 50 requests/hour demo limit. `--full` re-walks every page.
Photos you delete are remembered and never come back.

**First import of the existing site**: `npm run photos:export-seed` (repo root) writes
`backend/seed/curation.json`; then `python -m app.cli seed`. It costs about one Unsplash request per
photo, so a large library may need a second run after the hourly limit resets. Safe to repeat.

**Backups**: nightly copy of the database to `backups/YYYY-MM-DD.db` in the private bucket, 30 days
kept. To restore: stop the API, download a copy to `/var/lib/portfolio/portfolio.db`, start it.

**Lost your authenticator?** Use a recovery code at login. With none left, SSH to the server and run
`python -m app.cli reset-admin <username>`: it sets a new password, a new 2FA secret and new recovery
codes, clears any lockout, and signs out every existing session. Logging out in the admin also ends
the session on the server, not just in the browser.

**Contact messages**: every message is saved first. If Telegram is down, `portfolio-notify.timer`
retries every 5 minutes (`python -m app.cli notify-pending`); nothing is lost.

**Login protection**: 5 failures per IP + username, and 20 per username from any IP, lock logins for
15 minutes. That also means someone hammering your username can lock *you* out for 15 minutes;
`reset-admin` clears it.

## First deployment checklist

1. **Cloudflare DNS**: move `ntshptl.in` DNS to Cloudflare (keep GoDaddy as registrar). Recreate the
   existing records first, especially the `portfolio` CNAME to `nitishpatel.github.io`.
2. **R2**: create two buckets (public, private) and an API token with read/write on both.
   - Public bucket → custom domain `cdn.ntshptl.in`.
   - Private bucket → CORS rule allowing `PUT` (header `Content-Type`) from the origin that serves the
     admin UI, so the browser can upload straight to R2.
   - Don't add a lifecycle rule to clean `originals/`: it can't tell an abandoned upload from a live
     original. Abandoned uploads are rare and small.
3. **Telegram**: create a bot with @BotFather, message it once, read your chat id from
   `https://api.telegram.org/bot<token>/getUpdates`.
4. **Unsplash**: an application access key (demo tier is fine).
5. **Server** (smallest EC2 that has 1 GB RAM, e.g. `t4g.micro`; open ports 80/443 only):
   ```bash
   sudo useradd --system --home /opt/portfolio portfolio
   sudo mkdir -p /var/lib/portfolio /etc/portfolio && sudo chown portfolio: /var/lib/portfolio
   # copy this directory to /opt/portfolio/backend, then:
   cd /opt/portfolio/backend && uv sync --no-dev
   sudo install -m 600 -o portfolio /path/to/.env /etc/portfolio/backend.env   # DATABASE_URL=sqlite:////var/lib/portfolio/portfolio.db
   sudo ln -s /etc/portfolio/backend.env /opt/portfolio/backend/.env           # so the CLI reads it too
   sudo cp deploy/*.service deploy/*.timer /etc/systemd/system/ && sudo cp deploy/Caddyfile /etc/caddy/
   sudo -u portfolio .venv/bin/alembic upgrade head
   sudo -u portfolio .venv/bin/python -m app.cli create-admin <username>
   sudo systemctl enable --now portfolio-api portfolio-sync.timer portfolio-backup.timer portfolio-notify.timer caddy
   ```
6. DNS: `api.ntshptl.in` → the EC2 address, **DNS-only (grey cloud)** so the login lockout sees real
   client IPs (see the comment in `deploy/Caddyfile`).
7. Seed and check: `python -m app.cli seed`, then `curl https://api.ntshptl.in/health`.

The unit files and Caddyfile were written without access to `systemd-analyze` or `caddy`; run
`systemd-analyze verify /etc/systemd/system/portfolio-*.service` and `caddy validate` on the server
before enabling them.

## Updating

```bash
cd /opt/portfolio/backend && git pull && uv sync --no-dev
sudo systemctl restart portfolio-api    # runs `alembic upgrade head` first
```
