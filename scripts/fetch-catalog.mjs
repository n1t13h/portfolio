// Fetches the published photos and collections from the API and writes them as one JSON file
// that the site bundles at build time, so visitors never wait on (or depend on) the API.
//
//   node scripts/fetch-catalog.mjs [--if-missing] [--out <path>]
//   env: CATALOG_API_URL (default https://api.ntshptl.in)
//
// Any failure (network, non-2xx, bad JSON, no photos) exits 1 without touching the output file,
// so a bad API answer can never be published.

import { existsSync } from "node:fs";
import { rename, writeFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";

const TIMEOUT_MS = 20_000;

/** API photo -> site photo: no nulls, no empty exif, no allowDownload flag. */
export function normalizePhoto(p) {
  if (Object.keys(p.variants ?? {}).length === 0) {
    throw new Error(`Photo ${p.id} has no image sizes; the site could not show it.`);
  }
  const exif = Object.fromEntries(Object.entries(p.exif ?? {}).filter(([, v]) => v !== null && v !== undefined));
  const photo = { id: p.id, title: p.title, aspectRatio: p.aspectRatio, variants: p.variants };
  if (p.place) photo.place = p.place;
  if (Object.keys(exif).length > 0) photo.exif = exif;
  for (const key of ["unsplashId", "unsplashUrl", "downloadUrl"]) {
    if (p[key]) photo[key] = p[key];
  }
  return photo;
}

/** Fetches everything through `getJson(path)`; throws if anything is missing or failed. */
export async function buildCatalog(getJson) {
  const photos = (await getJson("/photos")).map(normalizePhoto);
  if (photos.length === 0) throw new Error("The API returned no photos; refusing to publish an empty site.");
  const summaries = await getJson("/collections");
  const collections = [];
  for (const { slug } of summaries) {
    const c = await getJson(`/collections/${encodeURIComponent(slug)}`);
    collections.push({
      ...c,
      covers: c.covers.map(normalizePhoto),
      chapters: c.chapters.map((ch) => ({ ...ch, photos: ch.photos.map(normalizePhoto) })),
      photos: c.photos.map(normalizePhoto),
    });
  }
  return { photos, collections };
}

function httpGetJson(base) {
  return async (path) => {
    const res = await fetch(base + path, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) throw new Error(`GET ${path}: HTTP ${res.status}`);
    return res.json();
  };
}

/** `[--if-missing] [--out <path>]`; `out` is undefined when not given (main picks the default). */
export function parseArgs(argv) {
  const outAt = argv.indexOf("--out");
  const out = outAt >= 0 ? argv[outAt + 1] : undefined;
  if (outAt >= 0 && (!out || out.startsWith("--"))) throw new Error("--out needs a file path");
  return { ifMissing: argv.includes("--if-missing"), out };
}

async function main(argv) {
  const args = parseArgs(argv);
  const ifMissing = args.ifMissing;
  const out = args.out ?? fileURLToPath(new URL("../src/data/photos/catalog.json", import.meta.url));
  if (ifMissing && existsSync(out)) return;

  const base = (process.env.CATALOG_API_URL ?? "https://api.ntshptl.in").replace(/\/$/, "");
  const catalog = await buildCatalog(httpGetJson(base));
  const tmp = `${out}.tmp-${process.pid}`;
  await writeFile(tmp, JSON.stringify(catalog, null, 2) + "\n");
  await rename(tmp, out); // atomic: readers see the old file or the new one, never half of it
  console.log(`Wrote ${catalog.photos.length} photos and ${catalog.collections.length} collections to ${out}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch((err) => {
    console.error(`Could not fetch the photo catalog: ${err.message}`);
    process.exit(1);
  });
}
