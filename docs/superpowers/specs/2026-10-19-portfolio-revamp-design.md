# Portfolio revamp — design

Date: 2026-10-19
Status: approved by owner, 2026-10-19

## Intent

Nitish is a software engineer (Software Craftsperson at Incubyte, previously Team Lead at Yodaplus) who is also a serious hobby photographer. The site has two jobs, in a fixed order of priority:

1. **Show the dev work first.** Visitors are hiring managers, founders and other developers. Within a few seconds they should know who he is, what he builds, and that he's open to work.
2. **Let people discover the photographer.** Photography is a real part of who he is, but it is opt-in. It lives on its own page and never competes with the dev work on the landing view.

The current site (bold kinetic Space Grotesk type, dark by default) is being replaced, not refined.

## Visual references (decided)

The direction was found by iterating on mockups; references the owner chose:

- **Landing page → [pego.work](https://pego.work)** (Bruno Justo Pego). White page, one clean sans, a confident one-line headline, three large work cards whose *visuals* carry the colour, a big paragraph that sharpens word by word on scroll, a ragged strip of personal photos, local time in the footer. Plus the intro from his [Dribbble shot](https://dribbble.com/shots/27198427-Portfolio-is-live): images cycling *inside* the wordmark while work cards float in around it.
- **Photography page → structure only from [roshanishah.com](https://www.roshanishah.com/)** (large photos, collections, stories). Its look (serif, green/gold) was explicitly rejected: the photography page must look like the same site as the landing page.

Approved mockups (open in a browser; they are the visual source of truth):

- `docs/superpowers/specs/mockups/landing.html`
- `docs/superpowers/specs/mockups/photography.html`

Rejected along the way, so don't drift back toward them: concept gimmicks (split screen, pannable canvas, camera-viewfinder UI), tiny-type "quiet minimal", black-and-white Swiss grids, colour-blocked Swiss palettes, and a photo page that looks like Unsplash's own browser (filter pills + big viewer + thumbnail strip).

## Goals

- Landing page that reads as dev-first in the first viewport.
- Photography page that feels personal and sequenced (essays), not like a stock gallery.
- One visual system across both pages.
- Photo data shaped so a future owned backend can replace the mock without touching UI components.
- Fast and responsive; works well on phones.

## Non-goals (this round)

- Building the photography backend or database. The owner wants to own one later; for now the frontend uses mock data.
- Project case-study pages. Work cards don't open detail pages yet. *(My call; see "Calls made".)*
- Blog / journal, music, reading sections.
- Dark mode (owner confirmed).

## Anti-goals

- Anything that makes a visitor work to find the dev work (extra clicks, gimmicky navigation).
- Coloured UI chrome used as the source of "vibrancy". Colour comes from imagery.
- Shipping the Unsplash API key (or the secret key) in the client bundle or the repo.

## Constraints

- Existing stack stays: Vite + React 18 + TypeScript + Tailwind + shadcn/Radix + framer-motion + react-router-dom v6 + @tanstack/react-query.
- Hosted on **GitHub Pages** at the custom domain **`portfolio.ntshptl.in`**, so Vite `base` stays `/`. Lovable is no longer used. Deploy is manual: `npm run build` here, then the `dist` output is copied into the separate repo `../nitishpatel.github.io` (remote `nitishpatel/nitishpatel.github.io`, branch `gh-pages`, which holds the `CNAME`) and committed there. Keep this flow; don't add a deploy workflow to this repo. The build must emit a **`404.html` copy of `index.html`** (the deploy repo has none today), otherwise GitHub Pages returns 404 for direct visits to `/photos`, `/photos/:slug` and `?photo=` links.
- Keep Microsoft Clarity analytics (in `index.html`).
- "Book a call" uses the existing Calendly popup (`https://calendly.com/nitishp74/30min`; widget script already in `index.html`).
- Real links: GitHub `https://github.com/nitishpatel/`, LinkedIn `https://linkedin.com/in/ntshptl/`, email `contact@ntshptl.in`, résumé `https://drive.google.com/file/d/1lJnzel5i3I2sT_K-zKzNwnAngtSkR-f4/view?usp=sharing`, Unsplash `https://unsplash.com/@ntshptl`, Instagram `https://instagram.com/ntshptl`.
- Photos are the owner's own Unsplash uploads (48 photos, Sony ZV-E10). Images are served from `images.unsplash.com` with size params.

## Visual system

- **Type:** Geist (Google Fonts) for everything, Geist Mono for small metadata (counts, camera settings). Replaces Space Grotesk/JetBrains Mono/Inter.
- **Colour:** white background; text `#0b0b0b`; secondary `#6b6b6b`; tertiary `#9a9a9a`; hairlines `#e7e7e7`; card/placeholder fill `#f1f1f0`; a single green status dot for "open to work". No other accent colours in chrome.
- **Shape and spacing:** 28px page gutter (16px on phones), max width ~1520px, 10px card radius, 1px hairline dividers between sections, generous vertical rhythm (~56px between sections).
- **Motion:** easing `cubic-bezier(.16,1,.3,1)`; slow, small movements (scale ≤ 1.04 on hover, 8–40px reveals). All non-essential motion is disabled under `prefers-reduced-motion`.
- **Nav (shared):** sticky, translucent white with backdrop blur, 64px tall. Left: "Nitish" (home). Centre: Work, About, Experience, Photography (current page underlined). Right: Résumé, Contact.

## Landing page `/`

Top to bottom (see `mockups/landing.html`):

1. **Intro (~3s).** Full-screen white overlay. Eight or so of his photos float in from the edges and settle; centred wordmark "nitish ▢ patel" where the gap opens into a rounded window cycling through 4–5 photos (~420ms each), then the overlay fades to reveal the page.
   - Plays once per browser session; click, scroll or any key skips it; not played at all under reduced motion.
2. **Hero.** Headline (one line on desktop, ~54px, weight 500, tight tracking) + subline: role, previous role, green dot + "Open to interesting work."
3. **Selected work.** Three equal cards (16:10 media on `#f1f1f0`, title, one-line description + stack). Media are bright, real-looking visuals of each project; the mockup's hand-built CSS visuals (chat UI, staking card, verified certificate) are acceptable stand-ins until real screenshots exist. Hover: media scales slightly. Projects: Agentic RAG, Liquid Staking, Doc Attestation (Insurance Broker is the 4th; three cards on the landing page).
4. **Where I thrive.** Two-column split: small kicker left, large paragraph right (~46px) that sharpens from blurred/faint to solid word by word as it scrolls into view; then three capability groups (title + one line).
5. **Experience.** Same split; rows of company / role / years: Incubyte — Software Craftsperson — 2025–now; Yodaplus — Team Lead — 2023–2025; Yodaplus — Software Engineer — 2021–2023.
6. **Through my lens.** Kicker + "See all photographs →" (to `/photos`). A single row of ~15 of his photos at their true aspect ratios with staggered heights (contact-sheet feel); hover lifts a photo; clicking one opens it in the photography lightbox (or goes to `/photos`; builder's choice).
7. **Contact.** Left: short heading + one line + "Book a call →" (Calendly popup). Right: GitHub, LinkedIn, Instagram, Email.
8. **Footer.** "© Nitish Patel" and live local time "HH:MM, India".

Nav items Work/About/Experience scroll to sections on `/` (from `/photos` they navigate to `/` and then scroll).

## Photography `/photos` and `/photos/:slug`

See `mockups/photography.html` (it holds both views plus the lightbox).

**Index `/photos`:**
- Headline "Photographs" + one-line intro (mentions the Sony ZV-E10).
- Collections as large typographic rows (number, title ~52px, place, frame count, year). Hovering a row dims the others and shows a small stack of that collection's photos that follows the cursor with easing and cycles every ~650ms. Clicking opens the essay. On touch devices there is no cursor stack; rows are plain links.
- "Every frame": square grayscale contact sheet of all photos (8 columns desktop), colour on hover. Clicking opens the **lightbox**.

**Essay `/photos/:slug`:**
- "← All collections", large title, intro paragraph, facts line (frames, where, camera, year).
- Chapters: numbered heading row with a one-line note, followed by photos laid out by aspect ratio: landscape → full width; two consecutive portraits → side-by-side pair; a lone portrait → offset (5/12 width) with its caption beside it, alternating sides. Each block fades/slides up as it enters the viewport.
- Every photo has a caption: title, plus mono metadata `place · focal length · aperture · shutter · ISO` when known.
- Ends with "Next collection →".

**Lightbox:** white translucent full-screen overlay; photo centred (never exceeding viewport); counter top-left; "Close · esc" top-right; ← → buttons and arrow keys; caption bar with title + metadata, "From <collection> →" (opens that essay) and "Unsplash ↗". Esc / backdrop click closes. Body scroll locked while open. Should be deep-linkable (e.g. `?photo=<id>`) so a frame can be shared (*builder may defer this*).

**Collections (mock content):**
- *Ujjain · Omkareshwar · Indore* (Madhya Pradesh, 2026, 22 frames, real Unsplash collection `jucoUVxFH9M`), chapters: Ujjain; Omkareshwar; Indore — Rajwada & Sarafa; Indore Zoo.
- *Mumbai* (home, 10 frames) and *Elsewhere* (11 frames): groupings proposed during design, not confirmed by the owner.
- Five weaker frames are excluded (keyboard, corn, two planes, night tower).

## Photo data (mock now, owned backend later)

- A typed data module is the single source of photo data, e.g. `Photo { id, unsplashId, src (base URL), width, height, title, place?, exif? { focalLength, aperture, shutter, iso, camera }, unsplashUrl }` and `Collection { slug, title, place, year, intro, coverIds, chapters: { title, note, photoIds }[] }`.
- UI reads data only through async functions (`getCollections()`, `getCollection(slug)`, `getPhotos()`) used via react-query, so a later backend swap is a change to those functions only.
- The mock is a **committed static snapshot** generated from the Unsplash API by a small script run locally with `UNSPLASH_ACCESS_KEY` from the environment. The key never goes in the repo or the bundle. The snapshot includes exif + location for all photos (the design-time fetch only covered the 22 Madhya Pradesh photos because of the 50 req/hour demo limit).
- The script fetches **all 48** photos (with exif and location) into a raw snapshot. Curation lives in a separate hand-edited file (collections, chapters, ordering, the excluded-frames list), so re-running the script never overwrites editorial choices. *(My call.)*
- The owner runs the script with their own key; the plan should make it a one-command step and document it in the README. Until it has been run, the builder seeds the snapshot from the mockup's `DATA` constant. *(My call.)*
- Exif and place are **optional** on every photo. Captions, the lightbox and the essay facts line must render cleanly without them (Unsplash doesn't always have exif). *(My call.)*
- Image URLs use Unsplash's size params (`w`, `q=80`, `auto=format`) appropriate to each slot; use `srcset` where it matters (essay and lightbox).

## Copy

Everything below is placeholder text written during design and **must be replaced or confirmed by the owner** before launch (builder should keep it in one obvious place):

- Hero headline ("I write software that's still easy to change a year later.").
- "Where I thrive" paragraph and the three capability lines.
- Work card descriptions beyond the existing one-liners; the fictional content inside card visuals (e.g. the "Aarav Mehta" certificate, ETH amounts).
- Contact heading/line, photography intros, chapter notes, the Mumbai/Elsewhere groupings.

## Decided with the owner

- **Light theme only** (owner confirmed): remove `ThemeProvider`'s dark default and the mode toggle; no dark tokens needed.
- **Replace the existing `/photos` cinematic page** and delete the unused `MusicPlaylist`, `Reading` and `BrowserFrame` components (owner confirmed).

## Calls made (owner to check)
- **No case-study pages** for projects this round; cards are not links (or link to an external repo/demo if one exists).
- **Intro plays once per session** and is skippable.
- Work, About and Experience stay as sections of `/`, not separate routes.

## Left to the builder

- Component breakdown, file layout, and how to share layout/nav between routes.
- Exact responsive breakpoints and the phone layouts (cards stack to one column; essay pairs/offsets collapse to single column; contact sheet drops to 3–4 columns; nav collapses sensibly).
- Animation implementation (framer-motion vs. CSS), smooth page transitions between `/` and `/photos`.
- Testing approach (there is no test setup today); sensible coverage for the data layer and essay layout logic.
- SEO/meta tags, Open Graph image, favicon.
- Whether the landing photo strip opens the lightbox directly or navigates to `/photos`.
