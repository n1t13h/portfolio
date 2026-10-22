# Portfolio backend — design

Date: 2026-10-22 · Status: draft for approval

## Intent

The portfolio frontend (Vite + React) currently reads photography data from two checked-in files: `src/data/photos/snapshot.json` (43 photos pulled from Unsplash by a manual script) and `src/data/photos/curation.ts` (hand-written order, exclusions, collections and chapters). Photos are hotlinked from Unsplash.

Build a small backend so that Nitish (the only admin) can add, curate, order and publish photos and collections without editing code, with originals stored cheaply in Cloudflare R2, and with the Unsplash feed replaced by an incremental sync.

## Goals

- Public read-only API serving published photos, collections and chapters in an admin-chosen order.
- Admin API behind password + TOTP 2FA for managing photos, collections and chapters.
- Photo storage in Cloudflare R2, served through a Cloudflare-fronted domain; the API never proxies image bytes.
- Incremental Unsplash → R2 sync that imports new photos as drafts.
- Per-photo opt-in downloads.
- Runs on the smallest practical EC2 (t4g.micro; t4g.nano if it fits) at near-zero monthly cost.
- One-time seed from `snapshot.json` + `curation.ts` so no existing curation is re-entered.

## Non-goals

- Multiple users, roles, signup, password reset by email (recovery is a CLI command on the server).
- Likes, comments, view counters, newsletter, visitor analytics.
- Server-side rendering or serving the frontend.
- The admin web UI. This spec covers the API only (see "Open questions").
- Non-JPEG uploads (HEIC, PNG, RAW).

## Anti-goals (failure even if it technically works)

- Full-resolution originals reachable without the per-photo download flag.
- Exact GPS coordinates leaking through public image variants.
- A cost surprise: any path where visitor traffic is billed per GB or hits the EC2 for image bytes.
- Losing the metadata database with the instance.

## Constraints

- Language/framework: Python, FastAPI (Nitish's preference). One uvicorn worker behind Caddy (automatic HTTPS).
- Database: SQLite via SQLAlchemy, Alembic migrations. Postgres later is a connection-string change, not a rewrite.
- Storage: Cloudflare R2 via the S3 API (boto3). Two buckets: public-variants (behind CDN domain) and private (originals + DB backups).
- Memory: must fit comfortably in 1 GB (ideally 512 MB) alongside Caddy.
- Existing frontend data shapes (`Photo`, `Collection`, `Chapter` in `src/data/photos/types.ts`) are the contract the public API should be able to satisfy with minimal frontend change.

## Decided with Nitish

- Cloudflare R2 for photos.
- FastAPI.
- Uploads are JPEG only.
- A photo belongs to at most one collection (one-to-one), via a chapter.
- Chapters stay a real concept; collections, chapters and photos are all orderable by the admin.
- Unsplash sync runs on a schedule (monthly by default), imports only photos not seen before, and imports them as **drafts**.
- Not every photo is on Unsplash: admin upload is a second entry point; after import both are identical.
- Downloads are off by default; the admin enables them per photo.
- Backend replaces the runtime Unsplash dependency. The frontend reads only from the backend.

## Data model

- **photo**: id, title, place (optional), aspect_ratio, exif (JSON: camera, focal_length, aperture, shutter, iso), taken_at (optional), status (`draft` | `published`), allow_download (bool, default false), sort_position (global order), chapter_id (nullable FK), position_in_chapter, unsplash_id (nullable, unique), unsplash_url (nullable), r2 keys (original, variants), created_at.
- **collection**: id, slug (unique), title, place, year, intro, status (`draft` | `published`), sort_position, cover photo ids (ordered list).
- **chapter**: id, collection_id, title, note, position.
- **admin**: single row: username, argon2 password hash, TOTP secret, recovery code hashes.
- **audit_log**: timestamp, action, target, ip.
- **sync_state**: last run, last result, remaining rate-limit budget.

A photo in no chapter is "standalone". A collection with no authored chapters is presented with one implicit untitled chapter. Deleting a collection or chapter un-assigns its photos; it does not delete them. The existing `excluded` list becomes `status = draft`.

## Public API (no auth)

- `GET /photos`: published photos in global order.
- `GET /collections`: published collections in admin order, with covers.
- `GET /collections/{slug}`: collection with chapters and photos, resolved like `ResolvedCollection` in the frontend types.
- `GET /photos/{id}/download`: 302 to a short-lived presigned URL of the download copy if `allow_download`; otherwise 404.
- `GET /health`.

Responses carry `Cache-Control` and `ETag` so Cloudflare can cache them and most traffic never reaches the EC2. Image URLs in responses point at the CDN domain.

## Admin API (session + 2FA)

- Auth: login (password then TOTP), logout, session check. Rate-limited and locked out after repeated failures. Session is an HttpOnly, Secure, SameSite=Strict cookie with a short lifetime, plus a custom-header CSRF check on state-changing calls.
- Photos: request upload (returns presigned R2 PUT URL), confirm upload (server validates it is a JPEG, extracts EXIF, builds variants), list all including drafts, edit metadata, publish/unpublish, toggle `allow_download`, delete, reorder.
- Collections and chapters: create, edit, delete, publish/unpublish, reorder collections, reorder chapters, assign/remove/reorder photos in a chapter, set covers.
- Sync: trigger now, trigger full resync, view last result.
- First admin is created by a CLI command on the server (prints the TOTP provisioning URI and recovery codes). There is no signup route.

## Images

- Accept only JPEG. The upload is verified by decoding it, not by trusting the extension or content type.
- On confirm, generate WebP variants at 800 / 1600 / 2400 px long edge, stripped of GPS and other EXIF, into the public bucket. EXIF fields needed for display are stored in the database.
- Originals go to the private bucket and are never public.
- If `allow_download`, visitors get a 2400 px long-edge JPEG (generated at upload) via presigned URL, not the original.
- Processing runs on the EC2 with Pillow, one image at a time, so memory stays bounded.

## Unsplash sync

- Scheduled with a systemd timer (monthly default).
- Lists the user's photos newest-first and stops at the first already-known Unsplash ID, so an empty run costs one API request.
- For each new photo: fetch details, call Unsplash's download-tracking endpoint, download the original, run the normal image pipeline, insert as `draft` with the Unsplash ID stored.
- The admin can also trigger a sync manually at any time, using the same incremental logic as the scheduled run (so it only fetches what is new). It starts in the background and returns immediately; the admin polls a status endpoint (running/finished, how many photos imported, any error, rate-limit budget left). Only one sync can run at a time: a second trigger while one is running is refused. "Full resync" is a separate, explicit action.
- Honours `X-Ratelimit-Remaining`; if the budget runs out, stops cleanly and resumes next run. The demo-tier limit is 50 requests/hour.
- Known limit: older photos edited or back-dated on Unsplash are not picked up; the admin "full resync" covers that.
- Imports photos only. Collections and chapters are authored in the admin.

## Seed / migration

A one-time script reads `snapshot.json` and `curation.ts`, downloads the 43 originals via the Unsplash sync path, and creates photos, collections, chapters, covers and ordering. Photos in `excluded` are created as drafts. After cutover the frontend stops importing the two data files and `photos:snapshot` is retired.

## Operations

- Deploy: Caddy + systemd service on EC2; config via environment file; R2 and Unsplash keys never in the repo.
- Backups: nightly SQLite `.backup` copy to the private bucket, 30 days retained.
- Logs: structured to journald; audit log in the database.
- Cost target: EC2 plus well under $1/month for R2 at this scale.

## Left to the builder

Project layout, library choices inside the stack above, exact endpoint paths and payload field names (as long as the public shapes map cleanly onto the frontend types), password and session parameters, migration tooling details, test strategy. Tests are expected for auth/2FA, ordering, the download flag, and sync dedupe.

## My calls (not yet agreed with Nitish)

- Backend lives in a `backend/` directory in this repo.
- Variants: WebP at 800 / 1600 / 2400; download copy is a 2400 px JPEG, not the original.
- GPS stripped from all public files.
- SQLite, with a nightly backup to R2.
- Monthly sync default; downloads are a redirect to a presigned URL.
- API served on its own subdomain, photos on a separate CDN subdomain.

## Admin path (decided)

The admin UI and every admin API route sit under a long random path prefix generated once and held in config (e.g. `/a/<random>`), not linked from anywhere and disallowed in `robots.txt`. This is an extra layer only; password + TOTP remain the real protection. The admin UI lives in the existing React app under that prefix, as a second phase after the API.

## Contact form + Telegram (decided)

- Public `POST /contact` (name, email, message). Rate-limited per IP, with a honeypot field and size limits.
- Every message is saved to the database first, then a Telegram Bot API `sendMessage` notifies Nitish. A Telegram failure never loses or rejects the message; it is logged and retried.
- Bot token and chat ID are config, not code. Nitish creates the bot via BotFather and supplies them.
- The frontend contact form itself is part of the frontend phase.

## Domains (decided)

Frontend: `portfolio.ntshptl.in`. My call: API at `api.ntshptl.in`, photos at `cdn.ntshptl.in`, both config values. Single-level subdomains because Cloudflare's free certificate covers one level. R2 custom domains require `ntshptl.in` DNS to be on Cloudflare (to be confirmed).

## Open questions

1. Is DNS for `ntshptl.in` on Cloudflare? If not, either move it or serve photos from R2's `r2.dev` URL (rate-limited, not for production) or put a Cloudflare-proxied hostname elsewhere.
