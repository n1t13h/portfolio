import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { orderForFetch, toSnapshotPhoto } from "./to-snapshot-photo.mjs";

const KEY = process.env.UNSPLASH_ACCESS_KEY;
if (!KEY) {
  console.error("UNSPLASH_ACCESS_KEY is not set. Run: UNSPLASH_ACCESS_KEY=... npm run photos:snapshot");
  process.exit(1);
}

const USER = "ntshptl";
const OUT = fileURLToPath(new URL("../src/data/photos/snapshot.json", import.meta.url));
const API = "https://api.unsplash.com";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let remaining = Infinity;
async function get(path) {
  const res = await fetch(`${API}${path}`, { headers: { Authorization: `Client-ID ${KEY}` } });
  const header = res.headers.get("X-Ratelimit-Remaining");
  if (header !== null) remaining = Number(header);
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

let existing = [];
try {
  existing = JSON.parse(await readFile(OUT, "utf8"));
} catch (err) {
  if (err.code !== "ENOENT") {
    console.error(`Could not read ${OUT}: ${err.message}. Fix or remove it; nothing was written.`);
    process.exit(1);
  }
}
const byId = new Map(existing.map((p) => [p.id, p]));

let stoppedEarly = false;
let fetched = 0;
try {
  const listed = [];
  for (let page = 1; ; page++) {
    const batch = await get(`/users/${USER}/photos?per_page=30&page=${page}`);
    listed.push(...batch);
    if (batch.length < 30) break;
    if (remaining <= 0) throw new Error("rate limit reached while listing");
    await sleep(1200);
  }
  const order = orderForFetch(listed.map((p) => p.id), byId.keys());
  for (const id of order) {
    if (remaining <= 0) {
      stoppedEarly = true;
      break;
    }
    await sleep(1200);
    const full = await get(`/photos/${id}`);
    byId.set(full.id, toSnapshotPhoto(full));
    fetched++;
    console.log(`fetched ${full.id}`);
  }
} catch (err) {
  stoppedEarly = true;
  console.error(String(err.message ?? err));
}

const out = [...byId.values()].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
await writeFile(OUT, JSON.stringify(out, null, 2) + "\n");
console.log(`Wrote ${out.length} photos (${fetched} refreshed) to ${OUT}`);
if (stoppedEarly) {
  console.log("Stopped early (rate limit or error). Existing entries were kept; re-run after an hour to finish.");
  process.exitCode = 2;
}
