# Portfolio Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current portfolio with a dev-first white landing page (pego.work-style) and a photography section of sequenced photo essays, both in one visual system, backed by a mock photo data layer built from Nitish's Unsplash uploads.

**Architecture:** React Router routes `/`, `/photos`, `/photos/:slug` share one nav/footer shell. All copy lives in `src/content/site.ts`. Photo data comes from a committed Unsplash snapshot (`snapshot.json`) plus a hand-edited curation file, exposed only through async functions consumed with react-query, so a later backend replaces those functions alone. Pure logic (data resolution, exif formatting, essay layout, intro gating) is unit-tested with Vitest; components get focused Testing Library tests.

**Tech Stack:** Vite 5, React 18, TypeScript, Tailwind 3, framer-motion 12, react-router-dom 6, @tanstack/react-query 5, Vitest + @testing-library/react + jsdom (added in Task 1).

**Spec:** `docs/superpowers/specs/2026-10-19-portfolio-revamp-design.md` (visual source of truth: `docs/superpowers/specs/mockups/landing.html`, `docs/superpowers/specs/mockups/photography.html` — open them in a browser and match them).

## Global Constraints

- Light theme only. No dark tokens, no theme toggle.
- Fonts: Geist (weights 300–600) for everything; Geist Mono (400, 500) for small metadata. Loaded from Google Fonts in `index.html`.
- Colours: text `#0b0b0b`; secondary `#6b6b6b`; tertiary `#9a9a9a`; hairline `#e7e7e7`; card/placeholder `#f1f1f0`; background `#ffffff`; status dot `#1fbf5f`. No other accent colours in UI chrome.
- Easing `cubic-bezier(.16,1,.3,1)`; hover scale ≤ 1.04; reveals 8–40px. Under `prefers-reduced-motion: reduce` all non-essential motion is off.
- Layout: page gutter 28px (16px below `sm`), max width 1520px, card radius 10px, hairline section dividers with ~56px vertical margin. Nav sticky, 64px, `rgba(255,255,255,.85)` + backdrop blur.
- Image URLs: `https://images.unsplash.com/photo-<pid>?w=<width>&q=80&auto=format`.
- Links: GitHub `https://github.com/nitishpatel/`, LinkedIn `https://linkedin.com/in/ntshptl/`, email `contact@ntshptl.in`, résumé `https://drive.google.com/file/d/1lJnzel5i3I2sT_K-zKzNwnAngtSkR-f4/view?usp=sharing`, Unsplash `https://unsplash.com/@ntshptl`, Instagram `https://instagram.com/ntshptl`, Calendly `https://calendly.com/nitishp74/30min` (popup via `window.Calendly.initPopupWidget`, script already in `index.html`).
- Never commit or bundle `UNSPLASH_ACCESS_KEY`; it is read from the environment by the snapshot script only.
- Keep Microsoft Clarity and the Calendly widget tags in `index.html`.
- Deploy stays manual (build here → copy `dist` into `../nitishpatel.github.io` on `gh-pages`, domain `portfolio.ntshptl.in`); Vite `base` stays `/`; build must emit `dist/404.html` identical to `dist/index.html`.
- All placeholder copy lives in `src/content/site.ts` (owner will replace it).

## Review Focus

1. **Deep links on GitHub Pages:** opening `/photos/<slug>` or `/photos?photo=<id>` directly must load the app (404.html fallback, Task 1), an unknown slug must show a "Collection not found" state with a link back (Task 9), and an unknown `?photo=` id must be ignored, not crash (Task 8).
2. **Photos without exif or place:** captions must show only the parts that exist — no leading/trailing/double `·` (Task 2).
3. **Curation that references a photo missing from the snapshot** (e.g. after re-running the script): drop it with a `console.warn`, never crash or render an empty slot (Task 2).
4. **Touch devices:** no cursor-following stack and no hover-only affordances; collection rows are plain links (Task 7).
5. **Lightbox lifecycle:** body scroll is restored on close *and* on unmount/route change; prev/next wrap around at both ends (Task 8).

---

## File Structure

```
index.html                                   modify: Geist fonts, title/meta
package.json                                 modify: test deps/scripts, postbuild 404, photos:snapshot
vite.config.ts                               modify: vitest config
src/test/setup.ts                            create: jest-dom + matchMedia/IntersectionObserver stubs
src/index.css                                modify: light tokens only
tailwind.config.ts                           modify: fonts, colours, easing
src/App.tsx                                  modify: routes, remove ThemeProvider
src/content/site.ts                          create: all copy, links, projects, experience
src/lib/unsplash.ts                          create: imgUrl, srcSet
src/lib/time.ts                              create: formatIndiaTime
src/data/photos/types.ts                     create: Photo, Exif, Collection, Chapter
src/data/photos/snapshot.json                create: raw photo snapshot (seeded from mockup)
src/data/photos/curation.ts                  create: collections/chapters/excluded (by photo id)
src/data/photos/index.ts                     create: getPhotos, getCollections, getCollection, resolveCollections
src/data/photos/format.ts                    create: formatPhotoMeta
src/data/photos/essayLayout.ts               create: buildEssayBlocks
scripts/unsplash-snapshot.mjs                create: snapshot generator
scripts/to-snapshot-photo.mjs                create: pure API→Photo transform (tested)
src/components/site/SiteNav.tsx              create
src/components/site/SiteFooter.tsx           create
src/components/site/ScrollToHash.tsx         create
src/components/home/Intro.tsx                create (+ shouldPlayIntro)
src/components/home/Hero.tsx                 create
src/components/home/WorkCards.tsx            create
src/components/home/work-visuals.tsx         create: RagVisual, StakeVisual, CertVisual
src/components/home/Thrive.tsx               create (BlurWords inside)
src/components/home/ExperienceList.tsx       create
src/components/home/LensStrip.tsx            create
src/components/home/Contact.tsx              create
src/components/photos/CollectionRows.tsx     create
src/components/photos/CursorStack.tsx        create
src/components/photos/ContactSheet.tsx       create
src/components/photos/Lightbox.tsx           create (+ useLightboxParam)
src/components/photos/EssayBlock.tsx         create
src/pages/Index.tsx                          rewrite
src/pages/Photos.tsx                         rewrite
src/pages/PhotoCollection.tsx                create
DELETE: src/components/{Navbar,Experience,ProjectsSection,Skills,MusicPlaylist,Reading,BrowserFrame,mode-toggle,theme-provider}.tsx
```

---

### Task 1: Foundation — test tooling, light design tokens, cleanup, 404 fallback

**Files:**
- Modify: `package.json`, `vite.config.ts`, `index.html`, `src/index.css`, `tailwind.config.ts`, `src/App.tsx`
- Create: `src/test/setup.ts`, `src/App.test.tsx`
- Delete: the nine components listed above; old `src/pages/Index.tsx` and `src/pages/Photos.tsx` bodies are replaced by placeholders here

**Interfaces:**
- Produces: `npm test` (= `vitest run`); Tailwind tokens `font-sans` = Geist, `font-mono` = Geist Mono, colours `ink` `#0b0b0b`, `mid` `#6b6b6b`, `soft` `#9a9a9a`, `line` `#e7e7e7`, `card` `#f1f1f0`, `ok` `#1fbf5f`; `transitionTimingFunction.out` = `cubic-bezier(.16,1,.3,1)`; routes `/`, `/photos`, `/photos/:slug` (placeholder pages `Index`, `Photos`, `PhotoCollection`), `*` → `NotFound`.

- [ ] **Step 1:** Install dev deps: `npm i -D vitest@^2 @testing-library/react@^16 @testing-library/jest-dom@^6 @testing-library/user-event@^14 jsdom@^25`. Add scripts `"test": "vitest run"`, `"test:watch": "vitest"`, `"postbuild": "cp dist/index.html dist/404.html"`. Add `test: { environment: "jsdom", setupFiles: "./src/test/setup.ts", globals: true }` to `vite.config.ts` (add `/// <reference types="vitest" />`). `src/test/setup.ts` imports `@testing-library/jest-dom/vitest` and stubs `window.matchMedia` (returns `matches: false` unless a test overrides it) and `IntersectionObserver`.

- [ ] **Step 2: Write the failing test** `src/App.test.tsx`

```tsx
it("routes /photos/:slug to the collection page", () => {
  window.history.pushState({}, "", "/photos/mumbai");
  render(<App />);
  expect(screen.getByTestId("page-photo-collection")).toBeInTheDocument();
});
it("does not render a theme toggle", () => {
  window.history.pushState({}, "", "/");
  render(<App />);
  expect(screen.queryByRole("button", { name: /toggle theme/i })).toBeNull();
});
```

- [ ] **Step 3:** Run `npx vitest run src/App.test.tsx` → FAIL (no `page-photo-collection`).

- [ ] **Step 4:** Implement: remove `ThemeProvider` from `App.tsx`; add the three routes with placeholder pages each rendering a root `data-testid` (`page-home`, `page-photos`, `page-photo-collection`); delete the nine old components and the old page bodies; replace `src/index.css` tokens with a single light set (radius `10px`, background white, foreground `#0b0b0b`), remove `.dark`; set `darkMode` out of `tailwind.config.ts` and add the fonts/colours/easing above; in `index.html` swap the Google Fonts link to `Geist:wght@300;400;500;600` + `Geist+Mono:wght@400;500`, title `Nitish Patel — Software Craftsperson`, description `Software craftsperson building agentic AI, DeFi and web products. Also a photographer.` (same text in og tags).

- [ ] **Step 5:** Run `npm test` → PASS. Run `npm run build && cmp dist/index.html dist/404.html && echo SAME` → prints `SAME`.

- [ ] **Step 6: Commit** `git commit -m "chore: light design tokens, vitest setup, new routes, 404 fallback"`

---

### Task 2: Photo data layer

**Files:**
- Create: `src/data/photos/types.ts`, `snapshot.json`, `curation.ts`, `index.ts`, `format.ts`, `src/lib/unsplash.ts`
- Test: `src/data/photos/index.test.ts`, `src/data/photos/format.test.ts`, `src/lib/unsplash.test.ts`

**Interfaces:**
- Produces:
  - `type Exif = { camera?: string; focalLength?: number; aperture?: number; shutter?: string; iso?: number }`
  - `type Photo = { id: string; pid: string; aspectRatio: number; title: string; place?: string; exif?: Exif; unsplashUrl: string }` (`id` = Unsplash photo id e.g. `"I5lzt9e4WMY"`; `pid` = the `photo-…` suffix e.g. `"1775585571531-1d0f9df8c144"`)
  - `type Chapter = { title: string; note: string; photoIds: string[] }`
  - `type Collection = { slug: string; title: string; place: string; year: string; intro: string; coverIds: string[]; chapters: Chapter[] }`
  - `type ResolvedChapter = Omit<Chapter,"photoIds"> & { photos: Photo[] }`; `type ResolvedCollection = Omit<Collection,"chapters"|"coverIds"> & { covers: Photo[]; chapters: ResolvedChapter[]; photos: Photo[] }`
  - `resolveCollections(snapshot: Photo[], curation: Curation): ResolvedCollection[]` (pure)
  - `orderPhotos(snapshot: Photo[], curation: Curation): Photo[]` (pure) — minus `excluded`, `order` first, then the rest in snapshot order
  - `getPhotos(): Promise<Photo[]>` — `orderPhotos` over the real snapshot and curation
  - `getCollections(): Promise<ResolvedCollection[]>`; `getCollection(slug: string): Promise<ResolvedCollection | null>`
  - `collectionOf(photoId: string, collections: ResolvedCollection[]): ResolvedCollection | undefined`
  - `formatPhotoMeta(p: Photo): string`
  - `imgUrl(pid: string, width: number): string`; `srcSet(pid: string, widths: number[]): string`
  - `type Curation = { order: string[]; excluded: string[]; collections: Collection[] }`

- [ ] **Step 1: Seed the data.** Build `snapshot.json` (array of `Photo`) and `curation.ts` from the `DATA` constant in `docs/superpowers/specs/mockups/photography.html` with a throwaway node one-liner (not committed): `id` from the `href` (`unsplash.com/photos/<id>`), `pid` as-is, `aspectRatio` = `r`, `title` = `desc`, `place` only if non-empty, `exif` mapped `mm→focalLength`, `f→aperture` (number), `s→shutter`, `iso→iso`, `camera: "Sony ZV-E10"` only when exif exists. Curation: the three collections with the mockup's slugs `ujjain-omkareshwar-indore`, `mumbai`, `elsewhere` (rename `mp`/`else` slugs), titles, places, years, intros, chapters, covers, all referenced by photo `id`; `order` = mockup photo order; `excluded` = `["HPwBe-5cilM", "y7i3Tvni0ZQ", "UzI1UZyMHbA", "Tnh9kZ7uM6U", "NE6hCD8cy8E"]` (keyboard, corn, two planes, night tower — not in the mockup data yet; they appear once Task 3's script runs).

- [ ] **Step 2: Write the failing tests**

```ts
// format.test.ts
const base = { id: "a", pid: "1-x", aspectRatio: 1.5, title: "T", unsplashUrl: "u" };
it("formats full metadata", () => {
  expect(formatPhotoMeta({ ...base, place: "Ram Ghat, Ujjain", exif: { focalLength: 38, aperture: 36, shutter: "4", iso: 640 } }))
    .toBe("Ram Ghat, Ujjain · 38mm · ƒ/36 · 4s · ISO 640");
});
it("omits missing parts without stray separators", () => {
  expect(formatPhotoMeta({ ...base, exif: { aperture: 5.6, shutter: "1/2500" } })).toBe("ƒ/5.6 · 1/2500s");
  expect(formatPhotoMeta({ ...base, place: "Mumbai" })).toBe("Mumbai");
  expect(formatPhotoMeta(base)).toBe("");
});

// index.test.ts
it("drops curated ids missing from the snapshot and warns", () => {
  const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
  const [c] = resolveCollections([photo("a")], { order: [], excluded: [], collections: [col({ coverIds: ["a", "ghost"], chapters: [{ title: "x", note: "", photoIds: ["ghost", "a"] }] })] });
  expect(c.chapters[0].photos.map(p => p.id)).toEqual(["a"]);
  expect(c.covers.map(p => p.id)).toEqual(["a"]);
  expect(warn).toHaveBeenCalledWith(expect.stringContaining("ghost"));
});
it("orderPhotos drops exclusions and follows order, then the rest", () => {
  expect(orderPhotos([photo("a"), photo("b"), photo("c")], { order: ["c"], excluded: ["b"], collections: [] }).map(p => p.id)).toEqual(["c", "a"]);
});
it("getCollection returns null for an unknown slug", async () => {
  expect(await getCollection("nope")).toBeNull();
});
it("real data: every collection has photos and the MP collection has 22", async () => {
  const cols = await getCollections();
  expect(cols.find(c => c.slug === "ujjain-omkareshwar-indore")!.photos).toHaveLength(22);
  cols.forEach(c => expect(c.photos.length).toBeGreaterThan(0));
});

// unsplash.test.ts
it("builds sized urls", () => {
  expect(imgUrl("1-x", 600)).toBe("https://images.unsplash.com/photo-1-x?w=600&q=80&auto=format");
  expect(srcSet("1-x", [400, 800])).toBe("https://images.unsplash.com/photo-1-x?w=400&q=80&auto=format 400w, https://images.unsplash.com/photo-1-x?w=800&q=80&auto=format 800w");
});
```

(`photo(id)` / `col(partial)` are small factories at the top of the test file.)

- [ ] **Step 3:** Run `npx vitest run src/data src/lib/unsplash.test.ts` → FAIL (modules missing).

- [ ] **Step 4:** Implement the interfaces above. `formatPhotoMeta` order: place, `${focalLength}mm`, `ƒ/${aperture}` (no trailing `.0`), `${shutter}s`, `ISO ${iso}`, joined with `" · "`, skipping undefined. `ResolvedCollection.photos` = chapters' photos flattened in order.

- [ ] **Step 5:** Run `npx vitest run src/data src/lib` → PASS.

- [ ] **Step 6: Commit** `git commit -m "feat: photo data layer with mock Unsplash snapshot"`

---

### Task 3: Unsplash snapshot script

**Files:**
- Create: `scripts/to-snapshot-photo.mjs`, `scripts/unsplash-snapshot.mjs`, `scripts/to-snapshot-photo.test.ts`
- Modify: `package.json` (`"photos:snapshot": "node scripts/unsplash-snapshot.mjs"`), `README.md`

**Interfaces:**
- Consumes: `Photo` shape from Task 2.
- Produces: `toSnapshotPhoto(apiPhoto: object): Photo` (named export, pure).

- [ ] **Step 1: Write the failing test**

```ts
it("maps an Unsplash API photo to a snapshot Photo", () => {
  const api = { id: "I5lzt9e4WMY", width: 2667, height: 4000, alt_description: "performer creating a fiery hoop with fire",
    urls: { raw: "https://images.unsplash.com/photo-1775585571531-1d0f9df8c144?ixid=abc" },
    links: { html: "https://unsplash.com/photos/I5lzt9e4WMY" },
    exif: { make: "Sony", model: "ZV-E10", focal_length: "38.0", aperture: "36.0", exposure_time: "4", iso: 640 },
    location: { name: "Ram Ghat, Kartik Chowk, Ujjain, Madhya Pradesh, India", city: "Ujjain" } };
  expect(toSnapshotPhoto(api)).toEqual({ id: "I5lzt9e4WMY", pid: "1775585571531-1d0f9df8c144", aspectRatio: 0.667,
    title: "Performer creating a fiery hoop with fire", place: "Ram Ghat, Ujjain",
    exif: { camera: "Sony ZV-E10", focalLength: 38, aperture: 36, shutter: "4", iso: 640 },
    unsplashUrl: "https://unsplash.com/photos/I5lzt9e4WMY" });
});
it("omits exif and place when Unsplash has none", () => {
  const p = toSnapshotPhoto({ ...minimal, exif: { make: null, model: null, focal_length: null, aperture: null, exposure_time: null, iso: null }, location: { name: null } });
  expect(p.exif).toBeUndefined(); expect(p.place).toBeUndefined();
});
```

- [ ] **Step 2:** Run `npx vitest run scripts` → FAIL.

- [ ] **Step 3:** Implement `toSnapshotPhoto`. Place rule: first comma segment of `location.name` + `, ` + `location.city` when city differs from that segment; just the first segment otherwise; drop `"India"`/state-only results. Title: first letter upper-cased, fallback `"Untitled"`. Aspect ratio rounded to 3 decimals. Camera: `"<make> <model>"` with make omitted if model already starts with it.

- [ ] **Step 4:** Implement `unsplash-snapshot.mjs`: exits with a clear message if `UNSPLASH_ACCESS_KEY` is unset; pages `GET /users/ntshptl/photos?per_page=30`, then `GET /photos/:id` per photo (for exif/location), sleeping 1.2s between calls; if `X-Ratelimit-Remaining` hits 0 it writes what it has and tells the user to re-run (keep previously fetched entries — merge by id); writes `src/data/photos/snapshot.json` sorted by id with 2-space JSON.

- [ ] **Step 5:** Run `npx vitest run scripts` → PASS. Add a README section "Updating photos": `UNSPLASH_ACCESS_KEY=… npm run photos:snapshot`, the 50 req/hour demo limit (re-run after an hour to finish), and that collections, order and exclusions live in `src/data/photos/curation.ts`.

- [ ] **Step 6: Commit** `git commit -m "feat: unsplash snapshot script"`

---

### Task 4: Essay layout algorithm

**Files:**
- Create: `src/data/photos/essayLayout.ts`
- Test: `src/data/photos/essayLayout.test.ts`

**Interfaces:**
- Produces: `type EssayBlock = { kind: "full"; photo: Photo } | { kind: "pair"; photos: [Photo, Photo] } | { kind: "offset"; photo: Photo; side: "left" | "right" }`; `buildEssayBlocks(photos: Photo[]): EssayBlock[]`

Rules (from the mockup): landscape = `aspectRatio > 1.1` → `full`. Two consecutive portraits → `pair`, but never two `pair`s back to back. Otherwise a lone portrait → `offset`; the image sits right (`side: "right"`) for the first offset after a pair or at the start, then sides alternate.

- [ ] **Step 1: Write the failing tests**

```ts
const L = (id) => ({ ...base, id, aspectRatio: 1.5 }), P = (id) => ({ ...base, id, aspectRatio: 0.667 });
it("lands landscapes full width", () => expect(kinds(buildEssayBlocks([L("a"), L("b")]))).toEqual(["full", "full"]));
it("pairs two portraits", () => expect(kinds(buildEssayBlocks([P("a"), P("b")]))).toEqual(["pair"]));
it("never pairs twice in a row", () => expect(kinds(buildEssayBlocks([P("a"), P("b"), P("c"), P("d")]))).toEqual(["pair", "offset", "pair"]));
it("alternates offset sides", () => {
  const b = buildEssayBlocks([P("a"), L("x"), P("b"), L("y"), P("c")]);
  expect(b.filter(x => x.kind === "offset").map(x => x.side)).toEqual(["right", "left", "right"]);
});
it("keeps every photo exactly once, in order", () => { /* flatten ids === input ids for a mixed list of 9 */ });
it("returns [] for no photos", () => expect(buildEssayBlocks([])).toEqual([]));
```

- [ ] **Step 2:** Run `npx vitest run src/data/photos/essayLayout.test.ts` → FAIL.
- [ ] **Step 3:** Implement `buildEssayBlocks`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: essay layout algorithm"`

---

### Task 5: Site shell — content, nav, footer, hash scrolling

**Files:**
- Create: `src/content/site.ts`, `src/lib/time.ts`, `src/components/site/SiteNav.tsx`, `SiteFooter.tsx`, `ScrollToHash.tsx`
- Modify: `src/App.tsx` (render `ScrollToHash` inside the router), the three placeholder pages (wrap in nav + footer)
- Test: `src/lib/time.test.ts`, `src/components/site/SiteNav.test.tsx`

**Interfaces:**
- Produces:
  - `site` object exported from `src/content/site.ts` with: `links` (all Global Constraints URLs), `hero { headline, sub, status }`, `projects: { id, title, description, stack, visual: "rag" | "stake" | "cert" }[]` (Agentic RAG / Liquid Staking / Doc Attestation with stack `AI, Vector DB` / `ETH, Solidity` / `Blockchain, Next.js`, descriptions from the mockup), `thrive { kicker: "Where I thrive", paragraph, capabilities: { title, line }[] }`, `experience: { company, role, years }[]` (three rows from the spec), `contact { heading, line, cta: "Book a call →" }`, `photos { intro }`. Copy values: take verbatim from the mockups.
  - `formatIndiaTime(d: Date): string` → `"HH:MM, India"` (24h, `Asia/Kolkata`)
  - `<SiteNav />`, `<SiteFooter />`, `<ScrollToHash />`

- [ ] **Step 1: Write the failing tests**

```ts
it("formats Asia/Kolkata time", () => expect(formatIndiaTime(new Date("2026-10-19T10:15:00Z"))).toBe("15:45, India"));
```
```tsx
it("underlines Photography on /photos routes", () => {
  render(<MemoryRouter initialEntries={["/photos/mumbai"]}><SiteNav /></MemoryRouter>);
  expect(screen.getByRole("link", { name: "Photography" })).toHaveAttribute("aria-current", "page");
});
it("points section links at the home page hashes", () => {
  render(<MemoryRouter initialEntries={["/photos"]}><SiteNav /></MemoryRouter>);
  expect(screen.getByRole("link", { name: "Work" })).toHaveAttribute("href", "/#work");
  expect(screen.getByRole("link", { name: "Résumé" })).toHaveAttribute("href", site.links.resume);
});
```

- [ ] **Step 2:** Run `npx vitest run src/lib/time.test.ts src/components/site` → FAIL.
- [ ] **Step 3:** Implement. Nav per Global Constraints: left "Nitish" → `/`; centre Work `/#work`, About `/#about`, Experience `/#experience`, Photography `/photos`; right Résumé (new tab) and Contact `/#contact`; on narrow screens the centre links collapse into a simple menu button + sheet (use existing `ui/sheet`). `ScrollToHash` smooth-scrolls to `location.hash` after navigation (instant under reduced motion), and to top otherwise. Footer: "© Nitish Patel" left, live `formatIndiaTime` (updates every 30s) right.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: site shell with nav, footer and content module"`

---

### Task 6: Landing page sections

**Files:**
- Create: `src/components/home/{Hero,WorkCards,work-visuals,Thrive,ExperienceList,Contact}.tsx`
- Modify: `src/pages/Index.tsx`
- Test: `src/pages/Index.test.tsx`, `src/components/home/Thrive.test.tsx`

**Interfaces:**
- Consumes: `site` (Task 5).
- Produces: section ids `work`, `about`, `experience`, `lens` (Task 8 fills it), `contact`; `<BlurWords text={string} />` inside `Thrive.tsx`.

- [ ] **Step 1: Write the failing tests**

```tsx
it("renders headline, three work cards and experience rows", () => {
  renderAt("/");
  expect(screen.getByRole("heading", { level: 1, name: site.hero.headline })).toBeInTheDocument();
  expect(within(document.getElementById("work")!).getAllByRole("heading", { level: 3 })).toHaveLength(3);
  expect(within(document.getElementById("experience")!).getByText("Incubyte")).toBeInTheDocument();
});
it("opens the Calendly popup from Book a call", async () => {
  const init = vi.fn(); (window as any).Calendly = { initPopupWidget: init };
  renderAt("/"); await userEvent.click(screen.getByRole("button", { name: /book a call/i }));
  expect(init).toHaveBeenCalledWith({ url: "https://calendly.com/nitishp74/30min" });
});
it("opens the email link when Calendly is unavailable", ...); // falls back to mailto:contact@ntshptl.in
```
```tsx
it("BlurWords shows every word solid under reduced motion", () => {
  mockMatchMedia("(prefers-reduced-motion: reduce)", true);
  render(<BlurWords text="one two three" />);
  screen.getAllByTestId("blur-word").forEach(w => expect(w).toHaveAttribute("data-in", "true"));
});
```

- [ ] **Step 2:** Run `npx vitest run src/pages/Index.test.tsx src/components/home` → FAIL.
- [ ] **Step 3:** Implement to match `mockups/landing.html`: hero (h1 ~54px weight 500 tracking `-.045em`; green dot `ok` + bold status); three 16:10 cards on `card` with the CSS visuals (chat bubbles with step chips; gradient staking card `#6d2bff→#2b3bff→#00c2ff`; tilted certificate with yellow `#ffcf24` "VERIFIED" seal) and hover scale 1.04; Thrive split 1fr/2fr with BlurWords (words go from opacity .12 + blur 6px to solid as scroll progress through the paragraph passes each word's index; progress = `(vh*.9 - top) / (height + vh*.35)` clamped 0–1); experience rows; contact block + socials row (GitHub, LinkedIn, Instagram, Email). Cards stack to one column below `md`; splits collapse to one column.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: landing page sections"`

---

### Task 7: Photos index page

**Files:**
- Create: `src/components/photos/{CollectionRows,CursorStack,ContactSheet}.tsx`
- Modify: `src/pages/Photos.tsx`
- Test: `src/pages/Photos.test.tsx`

**Interfaces:**
- Consumes: `getCollections`, `getPhotos`, `imgUrl` (Task 2); `site.photos.intro`.
- Produces: `<ContactSheet photos={Photo[]} onOpen={(id: string) => void} />`; `<CursorStack photos={Photo[]} active={boolean} />`.

- [ ] **Step 1: Write the failing tests**

```tsx
it("lists collections as links to their essays", async () => {
  renderAt("/photos");
  const row = await screen.findByRole("link", { name: /ujjain · omkareshwar · indore/i });
  expect(row).toHaveAttribute("href", "/photos/ujjain-omkareshwar-indore");
  expect(row).toHaveTextContent("22 frames");
});
it("renders every non-excluded photo in the contact sheet", async () => {
  renderAt("/photos");
  expect(await screen.findAllByTestId("sheet-photo")).toHaveLength((await getPhotos()).length);
});
it("does not render the cursor stack on touch devices", async () => {
  mockMatchMedia("(hover: none)", true);
  renderAt("/photos"); await screen.findAllByTestId("sheet-photo");
  expect(screen.queryByTestId("cursor-stack")).toBeNull();
});
```

- [ ] **Step 2:** Run `npx vitest run src/pages/Photos.test.tsx` → FAIL.
- [ ] **Step 3:** Implement to match the index view of `mockups/photography.html`: header; rows grid `60px 1fr 260px 90px 70px` (number, title ~52px, place, `N frames`, year), others dim to .3 on hover, title shifts 10px; CursorStack fixed-position, follows pointer with 0.14 lerp, offset (+30, −160), cycles `covers` every 650ms with small rotations (−4°, 3°, −1°, 5°), only when `(hover: hover)` and not reduced motion; ContactSheet 8 columns (4 below `md`, 3 below `sm`), square crops, grayscale → colour on hover, each a `button` labelled with the photo title. Loading state: skeleton rows (`ui/skeleton`).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: photography index with collection rows and contact sheet"`

---

### Task 8: Lightbox with deep links + landing photo strip

**Files:**
- Create: `src/components/photos/Lightbox.tsx`, `src/components/home/LensStrip.tsx`
- Modify: `src/pages/Photos.tsx` (open via sheet), `src/pages/Index.tsx` (add LensStrip in `#lens`)
- Test: `src/components/photos/Lightbox.test.tsx`, extend `src/pages/Index.test.tsx`

**Interfaces:**
- Consumes: `getPhotos`, `getCollections`, `collectionOf`, `formatPhotoMeta`, `imgUrl`, `srcSet`.
- Produces: `useLightboxParam(): { photoId: string | null; open(id: string): void; close(): void }` — state lives in the `?photo=<id>` search param (`replace` navigation); `<Lightbox photos={Photo[]} collections={ResolvedCollection[]} />` renders nothing when the param is null or unknown.

- [ ] **Step 1: Write the failing tests**

```tsx
it("opens from ?photo= and shows caption + metadata", async () => {
  renderAt("/photos?photo=I5lzt9e4WMY");
  expect(await screen.findByRole("dialog")).toHaveTextContent("Performer creating a fiery hoop with fire");
  expect(screen.getByRole("dialog")).toHaveTextContent("ƒ/36");
});
it("ignores an unknown ?photo= id", async () => {
  renderAt("/photos?photo=nope"); await screen.findAllByTestId("sheet-photo");
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("wraps around with arrow keys and closes on Escape, restoring scroll", async () => {
  renderAt(`/photos?photo=${firstId}`); await screen.findByRole("dialog");
  await userEvent.keyboard("{ArrowLeft}"); expect(currentCounter()).toMatch(new RegExp(`^${total} / ${total}$`));
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).toBeNull(); expect(document.body.style.overflow).toBe("");
});
it("restores body scroll when unmounted while open", ...);
it("links to the photo's collection essay", async () => {
  renderAt("/photos?photo=I5lzt9e4WMY");
  expect(await screen.findByRole("link", { name: /from ujjain · omkareshwar · indore/i })).toHaveAttribute("href", "/photos/ujjain-omkareshwar-indore");
});
```
```tsx
// Index.test.tsx
it("lens strip links each photo to the lightbox", async () => {
  renderAt("/");
  const links = await within(document.getElementById("lens")!).findAllByRole("link", { name: /photo:/i });
  expect(links.length).toBeGreaterThanOrEqual(12);
  expect(links[0].getAttribute("href")).toMatch(/^\/photos\?photo=/);
});
```

- [ ] **Step 2:** Run `npx vitest run src/components/photos src/pages/Index.test.tsx` → FAIL.
- [ ] **Step 3:** Implement to match the lightbox in `mockups/photography.html`: `role="dialog" aria-modal`, focus moves to Close and is trapped; white `rgba(255,255,255,.96)` + blur overlay; image `max-height: calc(100vh - 160px)` with `srcSet` [800, 1400, 2000]; counter `NN / total` (zero-padded) top-left; "Close · esc" top-right; ← → buttons + keys wrapping; backdrop click closes; caption bar: title + `formatPhotoMeta` (hidden when empty), "From <collection> →" link, "Unsplash ↗" (new tab); body overflow hidden while open, restored in effect cleanup. LensStrip: kicker "Through my lens" + "See all photographs →" (`/photos`); first 15 photos from `getPhotos()` at true aspect ratio, heights cycling `[150,200,130,180,160,210,140,190]`, horizontal overflow hidden (scrollable on touch), each a link `aria-label="Photo: <title>"` to `/photos?photo=<id>`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: deep-linkable lightbox and landing photo strip"`

---

### Task 9: Collection essay page

**Files:**
- Create: `src/pages/PhotoCollection.tsx`, `src/components/photos/EssayBlock.tsx`
- Test: `src/pages/PhotoCollection.test.tsx`

**Interfaces:**
- Consumes: `getCollection`, `getCollections`, `buildEssayBlocks`, `formatPhotoMeta`, `imgUrl`, `srcSet`, `Lightbox` (clicking an essay photo opens it via `?photo=`).

- [ ] **Step 1: Write the failing tests**

```tsx
it("renders title, facts and numbered chapters", async () => {
  renderAt("/photos/ujjain-omkareshwar-indore");
  expect(await screen.findByRole("heading", { level: 1, name: "Ujjain · Omkareshwar · Indore" })).toBeInTheDocument();
  expect(screen.getByText("Sony ZV-E10")).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 2 }).map(h => h.textContent)).toEqual(["Ujjain", "Omkareshwar", "Indore, Rajwada & Sarafa", "Indore Zoo"]);
});
it("shows a not-found state for an unknown slug", async () => {
  renderAt("/photos/nope");
  expect(await screen.findByText(/collection not found/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /all collections/i })).toHaveAttribute("href", "/photos");
});
it("links to the next collection, wrapping to the first", async () => {
  renderAt("/photos/elsewhere");
  expect(await screen.findByRole("link", { name: /next collection/i })).toHaveAttribute("href", "/photos/ujjain-omkareshwar-indore");
});
```

- [ ] **Step 2:** Run `npx vitest run src/pages/PhotoCollection.test.tsx` → FAIL.
- [ ] **Step 3:** Implement to match the essay view of `mockups/photography.html`: "← All collections"; header grid 1fr/1fr (title ~84px, tracking `-.055em`; intro ~23px; facts line Frames / Where / Camera / Year in mono labels); per chapter a row with top border in `ink`, number, h2 ~26px, note; `EssayBlock` renders `full` (max-height 86vh, cover), `pair` (two columns), `offset` (12-col grid: image cols 6–10 with caption cols 2–4 for `right`; mirrored for `left`); captions = title + `formatPhotoMeta`; blocks fade/slide up 40px when 12% visible (IntersectionObserver; instant under reduced motion); all collapse to single column below `md`; "Next collection → <title>" row at the end. Set `document.title` to `<collection> — Photographs — Nitish Patel`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: collection photo essays"`

---

### Task 10: Intro overlay

**Files:**
- Create: `src/components/home/Intro.tsx`
- Modify: `src/pages/Index.tsx`
- Test: `src/components/home/Intro.test.tsx`

**Interfaces:**
- Consumes: `getPhotos`, `imgUrl`.
- Produces: `shouldPlayIntro(storage: Pick<Storage,"getItem">, reducedMotion: boolean): boolean`; `INTRO_KEY = "intro-played"`; `<Intro onDone={() => void} />`.

- [ ] **Step 1: Write the failing tests**

```ts
it("plays once per session and never under reduced motion", () => {
  expect(shouldPlayIntro({ getItem: () => null }, false)).toBe(true);
  expect(shouldPlayIntro({ getItem: () => "1" }, false)).toBe(false);
  expect(shouldPlayIntro({ getItem: () => null }, true)).toBe(false);
});
it("treats an unavailable sessionStorage as already played", () => {
  expect(shouldPlayIntro({ getItem: () => { throw new Error("blocked"); } }, false)).toBe(false);
});
```
```tsx
it("skips on keydown and marks the session", async () => {
  const done = vi.fn(); render(<Intro onDone={done} />);
  await userEvent.keyboard("a");
  expect(done).toHaveBeenCalled(); expect(sessionStorage.getItem("intro-played")).toBe("1");
});
it("finishes by itself after 3200ms", () => { vi.useFakeTimers(); /* render, advance 3200, expect onDone */ });
```

- [ ] **Step 2:** Run `npx vitest run src/components/home/Intro.test.tsx` → FAIL.
- [ ] **Step 3:** Implement to match `mockups/landing.html` intro: fixed white overlay above everything; 9 photos float in from offsets (−40..40px) and settle over ~3.2s with staggered delays ≤ .25s; wordmark "nitish ▢ patel" (`clamp(72px, 9vw, 150px)`, weight 500, tracking `-.05em`) whose window opens from 0 to 1.9em width over 1s after .5s and cycles 5 photos every 420ms; at 3200ms (or on click / wheel / touchmove / keydown) set `INTRO_KEY` to `"1"`, fade out over 700ms, call `onDone`. Body scroll locked while visible. Index renders `<Intro>` only when `shouldPlayIntro(sessionStorage, prefersReducedMotion)` on first mount; preload the intro images.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: landing intro overlay"`

---

### Task 11: Final pass — responsive, meta, verification

**Files:**
- Modify: `index.html` (og:image `/site.jpeg`, `og:url` `https://portfolio.ntshptl.in/`), any component needing phone fixes, `README.md` (deploy steps)

- [ ] **Step 1:** Run `npm test` → all PASS; `npm run lint` → no errors; `npm run build` → succeeds and `cmp dist/index.html dist/404.html` prints nothing.
- [ ] **Step 2:** Run the app (`npm run dev`) and check in a browser at 1440px and 390px against both mockups: intro (and that reloading in the same tab skips it), every section, nav hash links from `/photos` back to `/`, collection hover stack (desktop only), essay layouts, lightbox from sheet / strip / essay, direct load of `/photos/mumbai?photo=<id>` via `npm run preview` after build. Fix what's off; commit each fix.
- [ ] **Step 3:** Check reduced motion (DevTools → Rendering → emulate `prefers-reduced-motion: reduce`): no intro, no blur, no slide-ins, nothing broken.
- [ ] **Step 4:** README "Deploy" section: `npm run build`, copy `dist/*` into `../nitishpatel.github.io` (keep its `CNAME`), commit and push `gh-pages`.
- [ ] **Step 5: Commit** `git commit -m "chore: final polish, meta and deploy docs"`
