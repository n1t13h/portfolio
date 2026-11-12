# Frontend API Switch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The public site gets its photos and collections from the live API at build time, serves
images from `cdn.ntshptl.in`, gains a contact form and a lightbox Download button, and deploys
itself to GitHub Pages on demand.

**Architecture:** A Node script fetches `/photos` and `/collections/{slug}` from the API before
`vite build` and writes `src/data/photos/catalog.json`. That file is bundled and read by the
existing async data functions, so nothing calls the API at runtime except the contact form. Tests
use a committed fixture of the same shape through a Vitest alias. A `workflow_dispatch` GitHub
Action runs tests, builds and deploys to Pages.

**Tech Stack:** React 18 + Vite + Vitest + Testing Library, shadcn/ui `Dialog`, Node 22 scripts,
FastAPI + pytest for the backend, GitHub Actions (`actions/deploy-pages`).

**Spec:** `docs/superpowers/specs/2026-11-12-frontend-api-switch-design.md`

## Global Constraints

- **No commits.** Nitish's standing rule: every "Commit" step below is replaced by "leave the
  change uncommitted". Don't run `git commit` or `git push`.
- **API base URL.** Use `VITE_API_URL` if set, else `http://localhost:8000` in dev, else
  `https://api.ntshptl.in`. The catalog script uses `CATALOG_API_URL`, defaulting to
  `https://api.ntshptl.in`.
- **Images only from the API's `variants`** (keys `"800"`, `"1600"`, `"2400"`). Nothing may
  reference `images.unsplash.com` after Task 3.
- **Exact copy:**
  - Contact link: `Send a message →`
  - Dialog title: `Send a message`
  - Dialog subtitle: `Tell me a bit about it. I usually reply within a day.`
  - Field labels: `Name`, `Email`, `What's on your mind?`
  - Button: `Send message`
  - Success: `Thanks, got it.` / `I'll reach out shortly.` with a `Close` button
  - Email field error: `That email doesn't look right.`
  - Send failure: `Couldn't send that. Try again in a bit, or email contact@ntshptl.in.`
  - Lightbox: `Download`
- **Contact limits** (mirroring `backend/app/schemas/contact.py`): name 1–100 characters, email at
  most 254 characters matching `^[^@\s]+@[^@\s]+\.[^@\s]+$`, message 1–5000 characters, and a
  hidden honeypot field `website` sent as `""`.
- **Unsplash download link:** `https://unsplash.com/photos/{unsplash_id}/download?force=true`
- **Visual design unchanged** apart from the contact link and dialog and the Download link (the
  lightbox's existing link style).
- **Node 22.** Backend commands run from `backend/` with `.venv/bin/pytest`. Frontend commands run
  from the repo root.

## Review Focus

1. **Old shared links:** `/photos?photo=I5lzt9e4WMY` (an Unsplash id, the current link format)
   still opens that photo, although API ids are hex. Test in Task 3.
2. **Photos with no EXIF:** the API sends all-`null` EXIF fields. The lightbox meta line must
   never show `null`, `undefined` or an empty `·`. Tests in Task 2 (normalisation) and Task 3
   (rendering).
3. **API down or partial at build time:** a timeout, a 5xx, an empty `/photos`, or a collection
   detail failing must stop the build and leave any existing `catalog.json` untouched. Test in
   Task 2.
4. **Contact double submit and failure:** pressing Send twice sends one request. A 429 or network
   failure keeps the typed text and shows the failure line. Test in Task 5.
5. **Missing image size:** a photo with fewer than three variants still gets a working
   `src`/`srcSet`, using the largest it has. Test in Task 3.

---

## File structure

| File | Responsibility |
|---|---|
| `backend/app/schemas/public.py` | Adds `unsplashId`, `unsplashUrl` to `PublicPhoto` |
| `backend/app/services/catalog.py` | Unsplash download redirect |
| `scripts/fetch-catalog.mjs` | Fetches the API and writes `catalog.json` (CLI + exported pure functions) |
| `scripts/fetch-catalog.test.ts` | Tests for the script's functions, with a stub fetch |
| `src/data/photos/types.ts` | New `Photo` shape |
| `src/data/photos/index.ts` | Reads `@/data/photos/catalog.json`, same exported functions |
| `src/test/fixtures/catalog.json` | Committed fixture: real catalog captured once from the API |
| `src/lib/images.ts` | `photoSrc`, `photoSrcSet` (replaces `src/lib/unsplash.ts`) |
| `src/lib/api.ts` | `apiBase()`, shared by the admin client and the contact form |
| `src/components/home/ContactDialog.tsx` | The contact modal and its form states |
| `src/content/site.ts` | Contact copy |
| `.github/workflows/deploy.yml` | On-demand Pages deploy |
| `docs/legacy-redirect/index.html` | Page to place in `nitishpatel/nitishpatel.github.io` |

---

### Task 1: Backend: Unsplash fields and Unsplash download redirect

**Files:**
- Modify: `backend/app/schemas/public.py` (class `PublicPhoto`)
- Modify: `backend/app/services/catalog.py` (`CatalogService.download_url`)
- Test: `backend/tests/unit/public/test_catalog_service.py`
- Test: `backend/tests/integration/public/test_public_api.py`

**Interfaces:**
- Produces: public photo JSON gains `"unsplashId": str | null` and `"unsplashUrl": str | null`.
  `GET /photos/{id}/download` redirects Unsplash photos to Unsplash.

- [ ] **Step 1: Write the failing unit tests** in `test_catalog_service.py`:

```python
def test_public_photos_carry_their_unsplash_id_and_page(service, fake_uow):
    with fake_uow as uow:
        uow.photos.add(photo("u", unsplash_id="I5lzt9e4WMY",
                             unsplash_url="https://unsplash.com/photos/x-I5lzt9e4WMY", **published()))
        uow.commit()
    [p] = service.photos()
    assert (p.unsplash_id, p.unsplash_url) == ("I5lzt9e4WMY", "https://unsplash.com/photos/x-I5lzt9e4WMY")

def test_an_unsplash_photo_downloads_from_unsplash(service, fake_uow):
    with fake_uow as uow:
        uow.photos.add(photo("u", unsplash_id="I5lzt9e4WMY", **published(allow_download=True)))
        uow.commit()
    assert service.download_url("u") == "https://unsplash.com/photos/I5lzt9e4WMY/download?force=true"

def test_an_unsplash_photo_with_downloads_off_is_still_refused(service, fake_uow):
    with fake_uow as uow:
        uow.photos.add(photo("u", unsplash_id="I5lzt9e4WMY", **published()))
        uow.commit()
    with pytest.raises(NotFound):
        service.download_url("u")
```

Add type hints to match the file's style. `published(**kw)` is in `tests/support/builders.py`.
The existing test `test_a_download_link_is_a_short_lived_private_link_to_the_download_copy` must
keep passing unchanged: it covers photos without an Unsplash id.

- [ ] **Step 2: Run them and confirm they fail**

Run: `cd backend && .venv/bin/pytest tests/unit/public/test_catalog_service.py -q`
Expected: the three new tests FAIL (missing attribute; R2 URL instead of Unsplash).

- [ ] **Step 3: Implement**
  - In `PublicPhoto`, add `unsplash_id: str | None = None` and `unsplash_url: str | None = None`.
    `CamelModel` emits camelCase.
  - In `download_url`, after the not-found checks, return the Unsplash link when
    `photo.unsplash_id`. Otherwise keep the presigned path.
  - The "no download copy" refusal applies only to photos without an `unsplash_id`.

- [ ] **Step 4: Integration test.** In `test_public_api.py`, add
  `test_unsplash_photo_download_redirects_to_unsplash`. It uses the existing `admin_client` /
  `add_published_photo` helpers if they can set an Unsplash id; otherwise it inserts through the
  app's unit of work the way the module's other fixtures do. It asserts:
  - a 302 with `location == "https://unsplash.com/photos/<id>/download?force=true"`
  - `cache-control == "no-store"`

- [ ] **Step 5: Run the whole backend suite and lint**

Run: `cd backend && .venv/bin/pytest -q && .venv/bin/ruff check app tests && .venv/bin/ruff format --check app tests`
Expected: all pass (≥ 518 tests).

- [ ] **Step 6: Deploy the backend**

Run: `cd backend && SSH_KEY=~/.ssh/craftclash-ec2.pem deploy/deploy.sh`
Expected: `API is healthy`. Then `curl -s https://api.ntshptl.in/photos | head -c 600` shows
`"unsplashId"`. The edge may serve a cached copy for up to 5 minutes.

- [ ] **Step 7: Leave uncommitted** (Global Constraints).

---

### Task 2: Catalog fetch script

**Files:**
- Create: `scripts/fetch-catalog.mjs`
- Test: `scripts/fetch-catalog.test.ts`
- Modify: `.gitignore` (add `src/data/photos/catalog.json`)
- Modify: `package.json` scripts

**Interfaces:**
- Consumes: the API from Task 1.
- Produces:
  - `normalizePhoto(apiPhoto) => Photo`: drops `null` fields in `exif`, and drops `exif` when
    nothing is left. Drops `allowDownload`, keeps `downloadUrl` only when non-null, keeps
    `unsplashId`/`unsplashUrl` only when non-null, keeps `variants` as is.
  - `buildCatalog(getJson: (path: string) => Promise<unknown>) => Promise<{ photos: Photo[], collections: ResolvedCollection[] }>`:
    calls `/photos`, `/collections`, then `/collections/{slug}` for each, in list order. It
    normalises every photo, including covers and chapter photos. It throws when `/photos` is empty
    or any call rejects.
  - CLI: `node scripts/fetch-catalog.mjs [--if-missing] [--out <path>]`.
    - Default out is `src/data/photos/catalog.json`.
    - `getJson` uses `fetch`, a 20 s timeout, and throws on non-2xx.
    - The file is written atomically (temp file + rename), only after `buildCatalog` resolves.
    - `--if-missing` exits 0 without fetching if the out file exists.
    - On error it prints the message and exits 1.
- npm scripts:
  - `"catalog:fetch": "node scripts/fetch-catalog.mjs"`
  - `"predev": "node scripts/fetch-catalog.mjs --if-missing"`
  - `"build": "npm run catalog:fetch && vite build && cp dist/index.html dist/404.html"`
  - Remove `photos:snapshot` and `photos:export-seed`.

- [ ] **Step 1: Write the failing tests** in `scripts/fetch-catalog.test.ts`. Follow the existing
  `scripts/to-snapshot-photo.test.ts` for how a `.mjs` is imported.
  - `normalizePhoto` on `{ exif: { camera: null, focalLength: null, aperture: null, shutter: null, iso: null }, ... }`
    returns an object with no `exif` key.
  - On `{ exif: { camera: "Sony ZV-E10", iso: 640, aperture: null } }` it returns
    `exif` equal to `{ camera: "Sony ZV-E10", iso: 640 }`.
  - On `{ downloadUrl: null, unsplashUrl: null, unsplashId: null, allowDownload: false }` it
    returns none of those four keys.
  - `buildCatalog` with a stub map `{ "/photos": [p1], "/collections": [{slug:"a"}], "/collections/a": {slug:"a", covers:[p1], chapters:[{title:"t", note:"n", photos:[p1]}], photos:[p1]} }`:
    returns one photo and one collection whose `chapters[0].photos[0]` is normalised.
  - `buildCatalog` rejects with `/no photos/i` when `/photos` returns `[]`.
  - `buildCatalog` rejects when the stub for `/collections/a` rejects (partial API).

- [ ] **Step 2: Run them and confirm they fail**

Run: `npx vitest run scripts/fetch-catalog.test.ts`
Expected: FAIL, the module is not found.

- [ ] **Step 3: Implement `scripts/fetch-catalog.mjs`** to the Interfaces above. Export
  `normalizePhoto` and `buildCatalog`, and run the CLI only when the file is executed directly
  (`import.meta.url === pathToFileURL(process.argv[1]).href`).

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `npx vitest run scripts/fetch-catalog.test.ts`
Expected: PASS.

- [ ] **Step 5: Atomic-write check (Review Focus 3).**

Run: `echo '{"keep":true}' > /tmp/c.json && CATALOG_API_URL=http://127.0.0.1:9 node scripts/fetch-catalog.mjs --out /tmp/c.json; echo "exit $?"; cat /tmp/c.json`
Expected: `exit 1`, and the file still reads `{"keep":true}`.

- [ ] **Step 6: Capture the fixture from the live API.** It holds real public data and must
  contain the slug `ujjain-omkareshwar-indore` and the Unsplash id `I5lzt9e4WMY`, which the
  existing tests rely on.

Run: `node scripts/fetch-catalog.mjs --out src/test/fixtures/catalog.json && node scripts/fetch-catalog.mjs`
Expected: both files are written, and `grep -c I5lzt9e4WMY src/test/fixtures/catalog.json` ≥ 1.
This needs Task 1 deployed.

- [ ] **Step 7: Leave uncommitted.**

---

### Task 3: Switch the site's data and images to the catalog

**Files:**
- Modify: `src/data/photos/types.ts`, `src/data/photos/index.ts`, `src/data/photos/index.test.ts`
- Modify: `src/data/photos/format.test.ts`, `src/data/photos/essayLayout.test.ts` (test photo literals)
- Create: `src/lib/images.ts`, `src/lib/images.test.ts`. Delete: `src/lib/unsplash.ts`, `src/lib/unsplash.test.ts`
- Modify (call sites): `src/components/home/LensStrip.tsx`, `src/components/home/Intro.tsx`,
  `src/components/intro/IntroStage.tsx`, `src/components/photos/ContactSheet.tsx`,
  `src/components/photos/EssayBlock.tsx`, `src/components/photos/Lightbox.tsx`,
  `src/components/photos/CursorStack.tsx`
- Modify: `vite.config.ts` (`test.alias`)
- Delete: `src/data/photos/snapshot.json`, `src/data/photos/curation.ts`,
  `scripts/unsplash-snapshot.mjs`, `scripts/export-curation.mjs`, `scripts/to-snapshot-photo.mjs`,
  `scripts/to-snapshot-photo.test.ts`
- Modify: `backend/README.md` ("First import of the existing site" paragraph: the seed has
  already run; its export script was removed on 2026-11-12)
- Test: `src/components/photos/Lightbox.test.tsx`

**Interfaces:**
- Consumes: the `catalog.json` shape from Task 2.
- Produces:
  - `type Photo = { id: string; title: string; place?: string; aspectRatio: number; exif?: Exif; variants: Record<string, string>; unsplashId?: string; unsplashUrl?: string; downloadUrl?: string }`.
    `ResolvedCollection` and `ResolvedChapter` keep their names and fields; `Collection`,
    `Chapter` and `Curation` are deleted.
  - `photoSrc(photo: Photo, width: number): string`: the URL of the smallest variant whose key is
    ≥ `width`, else the largest variant.
  - `photoSrcSet(photo: Photo): string`: every variant as `"<url> <key>w"`, ascending, joined with
    `", "`.
  - `getPhotos`, `getCollections`, `getCollection(slug)` and `collectionOf` keep their signatures.
    `index.ts` imports `@/data/photos/catalog.json` (this exact specifier; the test alias matches
    it).
  - `findPhoto(photos: Photo[], key: string): number`: the index of the photo whose `id` or
    `unsplashId` equals `key`, else `-1`. Lives in `index.ts`; the lightbox uses it for `?photo=`.

- [ ] **Step 1: Write the failing tests**
  - `src/lib/images.test.ts`, with `p` having variants 800/1600/2400:
    - `photoSrc(p, 500)` returns the 800 URL.
    - `photoSrc(p, 1400)` returns the 1600 URL.
    - `photoSrc(p, 3000)` returns the 2400 URL.
    - `photoSrcSet(p)` is `"…/800.webp 800w, …/1600.webp 1600w, …/2400.webp 2400w"`.
    - For a photo with only `{"800": a, "1600": b}`, `photoSrc(q, 2000) === b` (Review Focus 5).
  - `src/data/photos/index.test.ts`, replacing the `orderPhotos`/`resolveCollections` tests:
    - `findPhoto(photos, photos[0].id) === 0`
    - `findPhoto(photos, "I5lzt9e4WMY") >= 0`
    - `findPhoto(photos, "nope") === -1`
    - `getCollection("nope")` resolves to `null`.
  - `Lightbox.test.tsx`: keep the existing tests. They already open `?photo=I5lzt9e4WMY`, which is
    Review Focus 1. Add:
    - `it("shows no Unsplash link for a photo that isn't from Unsplash")`: render the lightbox for
      a fixture photo with `unsplashUrl` deleted (use a test-local copy), and assert
      `queryByRole("link", { name: /unsplash/i })` is null.
    - `it("never shows null or undefined in the meta line")`: for a fixture photo without `exif`,
      the dialog text contains neither `null` nor `undefined`.

- [ ] **Step 2: Add the Vitest alias** in `vite.config.ts` under `test`:
  `alias: [{ find: /^@\/data\/photos\/catalog\.json$/, replacement: path.resolve(__dirname, "./src/test/fixtures/catalog.json") }]`.

- [ ] **Step 3: Run the tests and confirm the new ones fail**

Run: `npx vitest run src/lib src/data src/components/photos/Lightbox.test.tsx`
Expected: FAIL (missing `images.ts` / `findPhoto`).

- [ ] **Step 4: Implement**
  - Rewrite `types.ts` and `index.ts` to the Interfaces.
  - Write `images.ts`.
  - Replace every `imgUrl(x.pid, w)` with `photoSrc(x, w)` and every `srcSet(x.pid, ws)` with
    `photoSrcSet(x)`. Keep each call site's existing width as the `w` argument and its existing
    `sizes` attribute.
  - Lightbox:
    - look up `?photo=` with `findPhoto`;
    - when navigating, write the photo's `unsplashId ?? id` to the URL, so links stay in the
      current format;
    - render the Unsplash link only when `photo.unsplashUrl`.
  - Update the photo literals in `format.test.ts` and `essayLayout.test.ts` to the new `Photo`
    type (drop `pid` and `unsplashUrl`, add `variants: {}`).
  - Delete the files listed above, and update the backend README paragraph.

- [ ] **Step 5: Run the full frontend suite, lint and a build**

Run: `npm test && npm run lint && npm run build`
Expected:
- tests and lint pass;
- the build writes `dist/404.html`;
- `grep -rl images.unsplash.com dist src --include=*.ts --include=*.tsx --include=*.js` prints
  nothing.

- [ ] **Step 6: Check it in a browser.** Run `npm run dev`. Then:
  - `/photos` shows images whose `src` starts with `https://cdn.ntshptl.in/`;
  - a collection page renders its chapters;
  - `/photos?photo=I5lzt9e4WMY` opens the fire-hoop photo.

- [ ] **Step 7: Leave uncommitted.**

---

### Task 4: Lightbox Download button

**Files:**
- Modify: `src/components/photos/Lightbox.tsx`
- Create: `src/lib/api.ts`, `src/lib/api.test.ts`
- Modify: `src/admin/api/client.ts` (use `apiBase()`; remove its local resolver)
- Test: `src/components/photos/Lightbox.test.tsx`

**Interfaces:**
- Produces: `apiBase(): string` in `src/lib/api.ts`. It returns `import.meta.env.VITE_API_URL`
  when set, else `http://localhost:8000` when `import.meta.env.DEV`, else
  `https://api.ntshptl.in`. The admin client's current behaviour is the reference.
- Consumes: `Photo.downloadUrl` (a path such as `/photos/<id>/download`) from Task 3.

- [ ] **Step 1: Write the failing tests**
  - `api.test.ts`: `apiBase()` returns `VITE_API_URL` when stubbed with `vi.stubEnv`, and
    `http://localhost:8000` under Vitest's DEV otherwise.
  - In `Lightbox.test.tsx`:
    - `it("shows Download only when the photo allows it")`: for a test-local fixture copy whose
      first photo has `downloadUrl: "/photos/abc/download"`, the link named `Download` has
      `href === apiBase() + "/photos/abc/download"`.
    - For a photo without `downloadUrl`, there is no `Download` link.

- [ ] **Step 2: Run them and confirm they fail**

Run: `npx vitest run src/lib/api.test.ts src/components/photos/Lightbox.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**
  - Write `api.ts`, and switch `src/admin/api/client.ts` to it.
  - In the lightbox's link row, before the Unsplash link, render
    `<a href={apiBase() + photo.downloadUrl}>Download</a>` with the same classes as the Unsplash
    link, only when `photo.downloadUrl`.

- [ ] **Step 4: Run the suite**

Run: `npm test && npm run lint`
Expected: PASS. The admin tests pass unchanged.

- [ ] **Step 5: Leave uncommitted.**

---

### Task 5: Contact dialog

**Files:**
- Create: `src/components/home/ContactDialog.tsx`, `src/components/home/ContactDialog.test.tsx`
- Modify: `src/components/home/Contact.tsx` (add the link that opens the dialog)
- Modify: `src/content/site.ts` (add `site.contact.message` with the copy from Global Constraints)

**Interfaces:**
- Consumes: `apiBase()` (Task 4) and `Dialog` from `@/components/ui/dialog`.
- Produces:
  - `ContactDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void })`.
  - `sendMessage(body: { name: string; email: string; message: string; website: string }): Promise<"sent" | { fieldErrors: Partial<Record<"name" | "email" | "message", string>> } | "failed">`,
    exported from the same file. It `POST`s JSON to `${apiBase()}/contact`, with no credentials.
    - 2xx returns `"sent"`.
    - 422 with FastAPI's `detail[].loc[1]` returns `fieldErrors`, mapping `email` to the email
      error copy and other fields to a generic `Please check this field.`
    - Anything else, or a thrown fetch, returns `"failed"`.

- [ ] **Step 1: Write the failing tests** in `ContactDialog.test.tsx`, with `fetch` stubbed by
  `vi.stubGlobal`:
  - Opening from the home page: `renderAt("/")`, click the link named `Send a message →`, and a
    dialog titled `Send a message` appears.
  - Client validation: submitting with email `nitish@` shows `That email doesn't look right.` and
    `fetch` is not called.
  - Success: fill valid values and click `Send message`. `fetch` is called once with
    `https://…/contact` (or the dev base), method `POST`, and a body equal to
    `{name, email, message, website: ""}`. Then `Thanks, got it.` and `I'll reach out shortly.`
    show, and the `Close` button closes the dialog.
  - Double submit (Review Focus 4): two quick clicks on `Send message` while the stubbed fetch is
    pending result in exactly one `fetch` call; the button is disabled while sending.
  - Failure keeps text (Review Focus 4): with fetch resolving 429, and separately rejecting, the
    failure line shows and the three fields still hold what was typed.
  - 422 mapping: with fetch resolving 422
    `{detail:[{loc:["body","email"],msg:"x"}]}`, the email error copy shows under Email.
  - Reset: after a success, closing and reopening shows empty fields.

- [ ] **Step 2: Run them and confirm they fail**

Run: `npx vitest run src/components/home/ContactDialog.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**
  - `ContactDialog`:
    - Labelled inputs (`<label>` text exactly as in the copy).
    - A visually hidden `website` input with `tabIndex={-1}` and `autoComplete="off"`.
    - Client checks per Global Constraints.
    - State: `idle | sending | sent | error`.
    - Underline-style inputs and the black pill button, as in the approved mockup.
  - `Contact.tsx`: under the existing "Book a call →" button, add a second button in the same
    style labelled `Send a message →` that opens the dialog. Keep it a `<button>`, since it opens
    a dialog rather than navigating.

- [ ] **Step 4: Run the full suite**

Run: `npm test && npm run lint`
Expected: PASS. The existing `Index.test.tsx` contact assertions still pass.

- [ ] **Step 5: End-to-end check against the live API.**
  - Run `npm run dev` and open `http://localhost:8080`, then `VITE_API_URL=https://api.ntshptl.in npm run dev`.
  - Send one real test message: Nitish gets a Telegram notification.
  - The live API only allows the `https://portfolio.ntshptl.in` origin, so from localhost the
    browser blocks the response. In that case, expect the failure line and confirm the request
    reached the API with status 202 in the browser's network panel. The real check happens after
    the cutover (Task 6, Step 6).

- [ ] **Step 6: Leave uncommitted.**

---

### Task 6: Deploy workflow, legacy redirect, cutover

**Files:**
- Create: `.github/workflows/deploy.yml`
- Create: `docs/legacy-redirect/index.html`
- Modify: `README.md` (repo root): a short "Deploying the site" section with the cutover steps
  and how to run the workflow

**Interfaces:**
- Consumes: `npm run build` (Task 2), which already fetches the catalog and writes `404.html`.

- [ ] **Step 1: Write `.github/workflows/deploy.yml`**
  - `name: Deploy site`, `on: workflow_dispatch`.
  - `permissions: { contents: read, pages: write, id-token: write }`.
  - `concurrency: { group: pages, cancel-in-progress: false }`.
  - Job `build`: `ubuntu-latest`. Steps:
    1. `actions/checkout@v4`
    2. `actions/setup-node@v4` with `node-version: 22` and `cache: npm`
    3. `npm ci`
    4. `npm test`
    5. `npm run lint`
    6. `npm run build`
    7. `actions/upload-pages-artifact@v3` with `path: dist`
  - Job `deploy`: `needs: build`, `environment: { name: github-pages, url: ${{ steps.deployment.outputs.page_url }} }`.
    Single step `actions/deploy-pages@v4` with `id: deployment`.

- [ ] **Step 2: Lint the workflow.**

Run: `npx --yes @action-validator/cli .github/workflows/deploy.yml`, or, if that's unavailable,
`python3 -c "import yaml,sys;yaml.safe_load(open('.github/workflows/deploy.yml'))"`
Expected: no errors.

- [ ] **Step 3: Write `docs/legacy-redirect/index.html`**: a minimal page that sends the visitor to
  `https://portfolio.ntshptl.in` + `location.pathname + location.search + location.hash`. It does
  this with JavaScript, with a `<meta http-equiv="refresh" content="0; url=https://portfolio.ntshptl.in/">`
  fallback and a visible link. The same file is also used as that repo's `404.html`.

- [ ] **Step 4: Write the README section.** It contains the four cutover steps exactly as in the
  spec's "Domain cutover" section:
  1. Old repo: remove the custom domain and replace its contents with `index.html` + `404.html`
     from `docs/legacy-redirect/`.
  2. New repo: Pages → Source: GitHub Actions; custom domain `portfolio.ntshptl.in`; Enforce
     HTTPS.
  3. Cloudflare: CNAME `portfolio` → `n1t13h.github.io`, DNS only.
  4. Actions → Deploy site → Run workflow.

- [ ] **Step 5: Hand the cutover to Nitish.** It needs his GitHub and Cloudflare accounts, and
  pushing this branch is his call under the no-commits rule. Stop here and tell him:
  - the branch must be on `main` of `n1t13h/portfolio` before the workflow can run;
  - the four steps, in order.

- [ ] **Step 6: Verify after Nitish runs it.**
  - `dig +short portfolio.ntshptl.in CNAME @1.1.1.1` returns `n1t13h.github.io.`
  - `curl -sI https://portfolio.ntshptl.in/photos/mumbai` returns `HTTP/2 404` with a
    `text/html` body containing the app's root element (the SPA fallback).
  - `curl -sI https://nitishpatel.github.io/` redirects to `portfolio.ntshptl.in`, or serves the
    redirect page.
  - In a browser on `portfolio.ntshptl.in`: images load from `cdn.ntshptl.in`, and one contact
    message sent from the live site arrives on Telegram.
