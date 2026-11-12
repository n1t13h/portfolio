# Nitish Patel — portfolio

Personal site at https://portfolio.ntshptl.in/ — Vite + React + TypeScript + Tailwind.

Routes: `/` (landing), `/photos` (photography), `/photos/:slug` (collection essays). A photo opens in the lightbox via `?photo=<id>` (its Unsplash id, or its API id for photos uploaded directly). Copy lives in `src/content/site.ts`.

## Develop

```sh
npm i
npm run dev            # dev server; fetches the photo catalog from the API the first time
npm run catalog:fetch  # refresh the local catalog after editing photos in the admin
npm test               # vitest (uses src/test/fixtures/catalog.json, never the network)
npm run lint
```

## Photos

Photos and collections are managed in the admin (`/a/<prefix>/photos`) and served by the API
(`backend/`, https://api.ntshptl.in). The site reads them **at build time**:
`scripts/fetch-catalog.mjs` writes `src/data/photos/catalog.json` (gitignored), which is bundled,
so visitors never wait on the API. Images come from `cdn.ntshptl.in`. The build fails, and nothing
is published, if the API is down or returns no photos. Admin changes reach the site on the next
deploy.

Set `CATALOG_API_URL` to build against another API (e.g. `http://localhost:8000`).

## Deploy

GitHub Actions publishes to GitHub Pages: **Actions → Deploy site → Run workflow**
(`.github/workflows/deploy.yml`). It runs the tests and lint, builds with fresh photos from the
API, and deploys. It only runs when started; merging to `main` does not deploy.

### One-time cutover from `nitishpatel.github.io`

The site used to be hand-built into the `gh-pages` branch of `nitishpatel/nitishpatel.github.io`.
To move it here, in this order:

1. **Old repo** (`nitishpatel/nitishpatel.github.io`): Settings → Pages → remove the custom domain.
   On `gh-pages`, replace everything (including `CNAME`) with `docs/legacy-redirect/index.html`,
   saved as both `index.html` and `404.html`. `nitishpatel.github.io/...` then forwards to the same
   path on `portfolio.ntshptl.in`.
2. **This repo** (`n1t13h/portfolio`): Settings → Pages → Source: **GitHub Actions**. Custom domain:
   `portfolio.ntshptl.in`. Tick **Enforce HTTPS** once GitHub has issued the certificate.
3. **Cloudflare DNS**: change the `portfolio` CNAME to `n1t13h.github.io`, **DNS only** (grey).
4. **Deploy**: Actions → Deploy site → Run workflow.

Expect a few minutes where `portfolio.ntshptl.in` may not load while GitHub issues the certificate.

## Intro links

The first load can pick its intro from the URL (the param name lives in `src/components/intro/variants.ts`):

- `/` and `/?intro=developer` play the intro with developer tiles (Temporal, agentic AI, Web3, Python, microservices, …). Developer is the default; `/` plays it once per session.
- `/?intro=photos` plays the photo intro and then lands on `/photos`.

An explicit variant plays even if the default intro already ran this session. Under reduced motion the animation is skipped, but `?intro=photos` still opens the photography page. Unknown values fall back to the default (developer) intro. The tiles are in `src/components/intro/devTiles.tsx`.
