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
  schemas/           every Pydantic request/response model, one module per entity
  models/            SQLAlchemy entities, one table per file
  repositories/      the only code that queries the database (abstract interface + SQL implementation)
  uow.py             AbstractUnitOfWork / SqlAlchemyUnitOfWork: one transaction with all repositories
  services/          use cases: business rules, built on the unit of work; return schemas, no HTTP
  api/public/        read-only routes + contact form (no login)
  api/admin/         everything under /a/<ADMIN_PATH_PREFIX>, behind login + 2FA; thin routers
  integrations/      the outside world behind small interfaces: storage (R2), unsplash, notifier (Telegram)
  core/              config, engine/session factory/Base, clock, security helpers, errors, limits
  cli.py             create-admin, reset-admin, sync, seed, backup, notify-pending
alembic/versions/    database migrations
deploy/              deploy.sh (laptop) + server-setup.sh, Caddy site, systemd units
tests/               unit/<entity>/ and integration/<entity>/, plus fakes/ and support/
```

**The layering** (each layer only knows the one below it):

```
router -> service -> unit of work -> repositories -> SQLAlchemy / SQLite
                  -> integrations (R2, Unsplash, Telegram)
```

- A **service method is one transaction**: `with self._uow() as uow: ...; uow.commit()`. Leaving the
  block without committing rolls everything back, so a service that fails halfway changes nothing.
  Services receive a unit-of-work *factory* because some (sync, seed, contact) run several short
  transactions in a row.
- Services never see a `Session`; they ask a repository. Entities do not leave a service: it
  returns schemas built inside the transaction, so nothing depends on a live session.
- **Row to model**: a response is built straight from the loaded row, `CollectionOut.model_validate(row)`,
  with no per-entity mapping helpers. Repositories hand back rows with their children loaded in display
  order (`collection.chapters`, `chapter.photos`), and anything a row cannot know (the CDN address of an
  image) comes in through the validation context, e.g.
  `PhotoOut.model_validate(photo, context={"public_url": storage.public_url})`. The one thing built by
  hand is the public collection's chapters and covers: they are filtered (drafts must not appear), so
  they must not be read from the ORM relationships.
- Repositories hold queries only. Business rules (slug format, lockouts, who may see what) live in
  services; the public-visibility rule lives in one place, `repositories/catalog.py`.
- Routers parse the request, call one service method and return its result. Pydantic models live in
  `app/schemas/`, nowhere else.
- All configuration comes from `app/core/config.py`; files stay small and single-purpose.

**Adding a feature**: add or extend a repository interface (and its SQL implementation), put the rule
in a service, unit test the service against `FakeUnitOfWork`, add a router, then one integration test
through HTTP. The fake is held to the same contract as the SQL repositories by tests that run against
both (`tests/integration/<entity>/test_*_repository.py`), so it cannot quietly drift.

**Tests**: `tests/unit/<entity>/` need no database or network (fake unit of work, fake storage,
fake Unsplash, fake clock); `tests/integration/<entity>/` use SQLite and the real app over HTTP;
`tests/fakes/` and `tests/support/` hold the shared fakes and builders.

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

## The admin UI

It lives in the React app (`src/admin/`), at `/a/<ADMIN_PATH_PREFIX>/photos` (also `collections`, `sync`).
The secret segment is read from the URL, never baked into the JavaScript bundle, and a wrong segment
shows the ordinary "Page not found". The admin is a separate lazy-loaded chunk, so the public site's
bundle is unchanged.

```bash
cd backend && docker compose up --build -d     # the API
cd .. && npm run dev                           # the site, on http://localhost:8080
# open http://localhost:8080/a/local-admin-path-0123456789/photos
```

- **Photos**: drag-and-drop or choose JPEGs (they go straight to storage, then the API processes them
  as drafts); filter drafts/published; click a photo to edit title/place, publish, allow downloads,
  assign it to a chapter, or delete; select several to publish/unpublish/delete at once; drag to reorder.
- **Collections**: create/edit/publish/reorder collections; chapters with notes; add photos from the
  library, drag to reorder them, star the covers.
- **Sync**: run the Unsplash sync or a full resync and see what happened.

The UI talks to `VITE_API_URL` (default `http://localhost:8000` in dev, `https://api.ntshptl.in` in a
production build) with the session cookie. Browsers that refuse `Secure` cookies on plain
`http://localhost` (Safari) can't sign in locally; use Chrome or Firefox.

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
uv run pytest                    # everything; add `tests/unit` for the fast, database-free suite
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

**First import of the existing site**: done on 2026-11-12 (`python -m app.cli seed`, 43 photos and 3
collections). The frontend export script that produced `backend/seed/curation.json` was removed the
same day, when the site switched to reading the API; the seed command stays for disaster recovery
from an old `curation.json`. It costs about one Unsplash request per photo and is safe to repeat.

**Backups**: nightly copy of the database to `backups/YYYY-MM-DD.db` in the private bucket, 30 days
kept. To restore: stop the API, download a copy to `/var/lib/portfolio/portfolio.db`, start it.

**Lost your authenticator?** Use a recovery code at login. With none left, SSH to the server and run
`python -m app.cli reset-admin <username>`: it sets a new password, a new 2FA secret and new recovery
codes, clears any lockout, and signs out every existing session. Logging out in the admin also ends
the session on the server, not just in the browser.

**Contact messages**: every message is saved first. If Telegram is down, `portfolio-notify.timer`
retries every 5 minutes (`python -m app.cli notify-pending`); nothing is lost.

**Login protection**: 5 failures per IP + username, and 20 per username from any IP, lock logins for
15 minutes. The per-username limit does not apply to an IP you successfully logged in from in the
last 30 days, so someone hammering your username from elsewhere cannot lock you out from your usual
connection. A new IP can still be locked for 15 minutes; `reset-admin` clears it.

**Audit log**: every admin action (and login) is written in the same transaction as the change
itself, so the two are saved together or not at all. Scheduled syncs and the seed are not audited.

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
5. **Server**: the API shares CraftClash's EC2 box (t4g.nano, `15.252.177.189`). The instance,
   firewall and IP are Terraform-managed in `~/code/craftclash/infra/terraform`; don't manage them
   from here. Caddy is shared too: this repo only owns `/etc/caddy/sites/portfolio.caddy`, the API
   listens on `127.0.0.1:8100` (CraftClash has 8000), and Caddy is reloaded, never restarted.
   From `backend/`:
   ```bash
   SSH_KEY=~/.ssh/craftclash-ec2.pem deploy/deploy.sh
   ```
   The first run creates `/etc/portfolio/backend.env` with a fresh admin path and session secret.
   Fill in the R2, Unsplash and Telegram keys there and deploy again; each timer stays off until
   its key is set. Then create the admin:
   ```bash
   ssh -i ~/.ssh/craftclash-ec2.pem ubuntu@15.252.177.189
   cd /opt/portfolio/backend && sudo -u portfolio .venv/bin/python -m app.cli create-admin <username>
   ```
   RAM is tight (the API is capped at `MemoryMax=300M`). If the box runs out, the fix is
   `t4g.micro` in the craftclash Terraform, which restarts both apps.
6. DNS: `api.ntshptl.in` A record → `15.252.177.189`, **proxied (orange)**. `deploy/portfolio.caddy`
   refuses anything not from Cloudflare and takes the visitor IP from `CF-Connecting-IP`. In
   Cloudflare: SSL/TLS mode **Full (strict)**, and a Cache Rule (Cloudflare doesn't cache JSON by
   default): hostname `api.ntshptl.in`, method `GET`, path starts with `/photos` or `/collections`
   → Eligible for cache, Edge TTL "Use cache-control header if present, bypass cache if not".
   The public responses say `max-age=300`, so admin edits show up within about 5 minutes.
7. Seed and check: `python -m app.cli seed`, then `curl https://api.ntshptl.in/health`.

## Updating

Run `deploy/deploy.sh` again. It backs up the database, syncs dependencies and restarts the API,
which applies new migrations (`alembic upgrade head`) before it starts.
