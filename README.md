# Nitish Patel — portfolio

Personal site at https://portfolio.ntshptl.in/ — Vite + React + TypeScript + Tailwind.

Routes: `/` (landing), `/photos` (photography), `/photos/:slug` (collection essays). A photo opens in the lightbox via `?photo=<id>`. Placeholder copy lives in `src/content/site.ts`.

## Develop

```sh
npm i
npm run dev      # dev server
npm test         # vitest
npm run lint
```

## Deploy

Deploys are manual, to the `gh-pages` branch of the `nitishpatel.github.io` repo checked out next to this one.

```sh
npm run build                      # emits dist/, plus dist/404.html (copy of index.html for SPA deep links)
# replace the old build but keep CNAME; set -e aborts before any delete if cd or checkout fails
set -e
cd ../nitishpatel.github.io
git checkout gh-pages
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name CNAME -exec rm -rf {} +
cp -R ../portfolio/dist/* .
git add -A
git commit -m "deploy: portfolio"
git push origin gh-pages
```

## Updating photos

```sh
UNSPLASH_ACCESS_KEY=... npm run photos:snapshot
```

This rewrites `src/data/photos/snapshot.json` from the Unsplash API, merging by photo id so existing entries are never lost. Photos not yet in the snapshot are fetched first, then existing ones are refreshed; refreshed entries are replaced with fresh Unsplash data (the snapshot is generated, editorial data lives in `curation.ts`). The demo API key allows 50 requests per hour; if the limit is hit the script saves what it has, so re-run after an hour to finish. Collections, order and exclusions live in `src/data/photos/curation.ts`.

## Intro links

The first load can pick its intro from the URL (the param name lives in `src/components/intro/variants.ts`):

- `/` and `/?intro=developer` play the intro with developer tiles (Temporal, agentic AI, Web3, Python, microservices, …). Developer is the default; `/` plays it once per session.
- `/?intro=photos` plays the photo intro and then lands on `/photos`.

An explicit variant plays even if the default intro already ran this session. Under reduced motion the animation is skipped, but `?intro=photos` still opens the photography page. Unknown values fall back to the default (developer) intro. The tiles are in `src/components/intro/devTiles.tsx`.
