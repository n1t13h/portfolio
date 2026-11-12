# Frontend switch to the API, contact form, and Pages deploy

Date: 2026-11-12. Status: draft for Nitish's review.

## Why

The backend is live at `https://api.ntshptl.in` (behind Cloudflare, public GETs cached) with all 43
photos and 3 collections seeded and images on `https://cdn.ntshptl.in`. The public site still reads a
hand-maintained `src/data/photos/snapshot.json` + `curation.ts` and loads images from
`images.unsplash.com`, so edits made in the admin never reach visitors. Separately, the site has no
way to message Nitish except a mailto link, and it is deployed by hand-committing build output into
another repo (`nitishpatel/nitishpatel.github.io`, last pushed 2026-10-19), so the revamp is not
reliably what visitors see.

This work makes the admin the source of truth for photos, adds a contact form, and gives this repo
its own one-click deploy to GitHub Pages.

## Goals

1. The public site shows photos and collections from the API, with images from `cdn.ntshptl.in`.
2. Pages stay as fast as today and keep working when the API server is down.
3. Admin edits reach the site when Nitish runs a deploy. A delay of a few hours is fine (his words).
4. A contact form, next to "Book a call", that sends messages to the API (which notifies Nitish on
   Telegram).
5. A Download button in the lightbox on photos where downloads are allowed.
6. `n1t13h/portfolio` deploys itself to GitHub Pages at `portfolio.ntshptl.in`, on demand.
7. `nitishpatel.github.io` keeps sending visitors to `portfolio.ntshptl.in`.

## Non-goals

- Fetching photo data in the visitor's browser (decided: data is baked in at build time).
- A scheduled rebuild or an admin "Publish" button (possible later; on demand only for now).
- An inbox page in the admin. Nitish replies to messages by email himself.
- Showing Unsplash photos from Unsplash's image CDN. All images come from `cdn.ntshptl.in`.
- Fixing Zoho mail DNS (MX records). Tracked separately; it only affects the form's error fallback.

## Anti-goals (would be a failure even if it "works")

- Visitors see a loading spinner, an empty photo page, or an error because the API is slow or down.
- A deploy publishes an empty or partial catalog because the API answered badly during the build.
- `nitishpatel.github.io` starts showing the old pre-revamp site.
- Image traffic causes meaningful R2 reads (images must stay cacheable at Cloudflare's edge).

## Decisions made with Nitish

- **Build-time data.** The site's photo data is fetched from the API during the build and bundled.
  The contact form is the only part that talks to the API at runtime.
- **On-demand deploys.** A GitHub Actions workflow in this repo, started with "Run workflow".
- **This repo owns Pages.** `portfolio.ntshptl.in` moves from `nitishpatel/nitishpatel.github.io` to
  `n1t13h/portfolio`. The old repo becomes a redirect page.
- **Downloads of Unsplash photos come from Unsplash, at full resolution.** Photos uploaded directly
  (no Unsplash id) keep using the 2400 px copy in R2.
- **Download button** appears in the lightbox only when the photo allows downloads.
- **Contact form placement and flow** (approved mockup `.superpowers/brainstorm/*/content/contact-modal.html`):
  - The Contact section is unchanged except for a second link, "Send a message →", under
    "Book a call →".
  - The link opens a modal dialog: title "Send a message", subtitle, fields Name, Email,
    "What's on your mind?", and a "Send message" button.
  - On success the dialog reads "Thanks, got it." / "I'll reach out shortly." with a Close button.
  - Field errors show under the field ("That email doesn't look right."). If sending fails: "Couldn't
    send that. Try again in a bit, or email contact@ntshptl.in." The typed text is kept.

## Design

### Backend (small)

1. **`unsplashUrl` in public photos.** Add `unsplash_url: str | None` to `PublicPhoto`
   (`backend/app/schemas/public.py`). The lightbox links to it today.
2. **Download redirect for Unsplash photos.** In `CatalogService.download_url`
   (`backend/app/services/catalog.py`), when the downloadable photo has an `unsplash_id`, return
   `https://unsplash.com/photos/{unsplash_id}/download?force=true` instead of a presigned R2 URL.
   It stays behind the same checks: the photo is published and `allow_download` is on. Photos
   without an `unsplash_id` keep the presigned R2 link. The endpoint's `Cache-Control: no-store`
   stays.
3. Tests for both, in the existing `tests/unit` / `tests/integration` layout. Then redeploy with
   `backend/deploy/deploy.sh`.

### Build-time catalog

- **`scripts/fetch-catalog.mjs`** (npm script `catalog:fetch`). It requests `GET /photos`,
  `GET /collections`, and `GET /collections/{slug}` for each collection (the list endpoint has no
  chapters). It writes one file, `src/data/photos/catalog.json` (gitignored), with the shape
  `{ photos: Photo[], collections: ResolvedCollection[] }`.
  - Base URL: `CATALOG_API_URL`, defaulting to `https://api.ntshptl.in`.
  - **Fails the build** (non-zero exit, no file written) on any non-2xx response, network error,
    malformed JSON, or zero photos. This is what keeps a bad API answer from being published.
  - Normalises the API's EXIF: it drops `null` fields, and drops `exif` entirely when nothing is
    left, so `formatPhotoMeta` keeps working unchanged.
- **`npm run build`** runs `catalog:fetch` and then `vite build`.
- **`npm run dev`** runs `catalog:fetch` only when `catalog.json` is missing, so local dev does not
  hit the API on every start. Run `npm run catalog:fetch` to refresh it.
- **Unit tests** use fixtures, never the network. Vitest aliases `src/data/photos/catalog.json` to
  a committed fixture, `src/test/fixtures/catalog.json` (a few photos and one collection in the
  API's shape), so tests pass on a fresh checkout and in CI, where the real file doesn't exist yet.
- **`src/data/photos/index.ts`** imports `catalog.json` and keeps its public functions:
  `getPhotos`, `getCollections`, `getCollection(slug)`, `collectionOf`. Pages and components are
  untouched at that level. `orderPhotos` and `resolveCollections` go away, because ordering,
  exclusion and resolving are now done by the API.

### Types and images

- `Photo` becomes
  `{ id, title, place?, aspectRatio, exif?, variants: { "800": url, "1600": url, "2400": url }, unsplashUrl?, downloadUrl? }`.
  `pid` is removed. `ResolvedCollection` keeps its current shape, which the collection detail
  endpoint already returns.
- Replace `imgUrl(pid, w)` / `srcSet(pid, widths)` in `src/lib/unsplash.ts` with helpers on a photo:
  - `photoSrc(photo, w)` picks the smallest variant that is at least `w`, capped at 2400.
  - `photoSrcSet(photo)` lists all three variants with `w` descriptors.

  Update the seven call sites: LensStrip, Intro, IntroStage, ContactSheet, EssayBlock, Lightbox,
  CursorStack. Rename the module, e.g. `src/lib/images.ts`.
- The lightbox shows "View on Unsplash" only when `unsplashUrl` is present.
- The lightbox shows a **Download** link when `downloadUrl` is present. The API returns a path, so
  the link is `https://api.ntshptl.in{downloadUrl}`, opened directly; the API redirects to the file.

### API base URL

One shared helper, used by both the admin client and the contact form:
- `VITE_API_URL` if set,
- otherwise `http://localhost:8000` in dev,
- otherwise `https://api.ntshptl.in`.

This is moved out of `src/admin/api/client.ts`.

### Contact form

- Component: `ContactDialog`, built on the existing shadcn `Dialog` (`src/components/ui/dialog.tsx`),
  opened from the new link in `src/components/home/Contact.tsx`. Copy goes in `src/content/site.ts`.
- Request: `POST {api}/contact` with JSON `{ name, email, message, website }`. `website` is the
  honeypot: a hidden field real visitors never fill. No credentials are sent. The API answers 202
  on success.
- Client-side checks mirror the API's: name 1–100 characters, a valid-looking email, message
  1–5000 characters.
- States: idle → sending (button disabled) → sent, or error.
  - A 422 maps its field errors under the fields.
  - A 429, a network failure or a 5xx shows the general failure line.
  - In every error case the typed text is kept.
- Closing the dialog after a successful send resets the form.

### SPA fallback on Pages

GitHub Pages has no rewrites, so deep links (`/photos/mumbai`, `/a/<prefix>/...`) would 404. The
build copies `dist/index.html` to `dist/404.html` so the router handles every path.

### Deploy workflow

`.github/workflows/deploy.yml`:
- Trigger: `workflow_dispatch` only.
- Permissions: `pages: write`, `id-token: write`, `contents: read`. Concurrency group `pages`, so
  runs don't overlap.
- Steps:
  1. Checkout.
  2. `actions/setup-node` with Node 22 and npm cache.
  3. `npm ci`.
  4. `npm test` and `npm run lint`.
  5. `npm run build`, which fetches the catalog first.
  6. Add the `404.html` copy.
  7. `actions/upload-pages-artifact` with `dist`.
  8. `actions/deploy-pages`.
- Expected run time is about a minute. Minutes are free, because the repo is public.
- If the catalog fetch fails, the run fails and the live site is untouched.

### Domain cutover (manual, one time, in this order)

1. **Old repo.** In `nitishpatel/nitishpatel.github.io`, remove the custom domain in Settings → Pages,
   then replace the repo's contents with a redirect page: `index.html` and `404.html`, both sending
   the visitor to `https://portfolio.ntshptl.in` + the same path. GitHub allows a custom domain on
   only one repo, so this frees it.
2. **New repo.** In `n1t13h/portfolio`, go to Settings → Pages → Source: GitHub Actions. Set the
   custom domain to `portfolio.ntshptl.in`, then turn on Enforce HTTPS once the certificate is
   issued.
3. **DNS.** In Cloudflare, point the `portfolio` CNAME at `n1t13h.github.io` (it is
   `nitishpatel.github.io` today). Keep it grey (DNS only).
4. **Deploy.** Run the deploy workflow.

Expect a few minutes when `portfolio.ntshptl.in` may fail while GitHub issues the certificate.

### Cleanup

Delete `snapshot.json`, `curation.ts`, their tests, `scripts/unsplash-snapshot.mjs`,
`scripts/export-curation.mjs`, `scripts/to-snapshot-photo.mjs` and its test, and the
`photos:snapshot` / `photos:export-seed` npm scripts. The seed is done.

Update `backend/README.md`: the "first import" step now describes a one-off that has already run, and
it should say that its export script no longer exists.

## Constraints

- No commits: changes are left uncommitted for Nitish (standing rule), unless he asks.
- The API server is a shared t4g.nano. Builds hit Cloudflare's cache for `/photos` and
  `/collections`, so a deploy costs the server almost nothing.
- Don't change the visual design beyond the approved contact link and dialog, and the Download
  button. The Download button follows the lightbox's existing link style.

## Calls I made (Nitish to check)

- **Deploys are on demand only.** Merging code does not deploy it; run the workflow. Adding
  `push: main` later is one line.
- **Build fails on a bad API response,** rather than falling back to an old catalog.
- **Tests run against a committed fixture catalog** (Vitest alias), not live API data.
- **`404.html` is a copy of `index.html`.** Deep links work, though GitHub serves them with a 404
  status; acceptable for this site.
- **Dev fetches the catalog once** and reuses it.
- **Modal subtitle copy:** "Tell me a bit about it. I usually reply within a day."
- **Download button label and placement:** "Download", next to "View on Unsplash" in the lightbox.
- **Unsplash photos download full-size from Unsplash.** The 2400 px copies already stored in R2 for
  them are left in place, unused.

## Risks

- **Cloudflare blocking the build.** Cloudflare bot protection could challenge requests from GitHub's
  runners. Bot Fight Mode is off by default; if a build fails with a 403 from the API, that is the
  cause.
- **The fallback email bounces.** The form's error fallback mentions `contact@ntshptl.in`, which only
  works once the Zoho MX records are restored.
