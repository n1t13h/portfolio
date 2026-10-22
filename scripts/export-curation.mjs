// Writes backend/seed/curation.json: the photo snapshot plus the hand-written curation
// (order, collections, chapters), in the shape the backend's `seed` command reads.
//
//   node scripts/export-curation.mjs [output-path]
//
// Node 22 runs the TypeScript curation file directly (types are stripped).
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const out = process.argv[2] ?? fileURLToPath(new URL("../backend/seed/curation.json", import.meta.url));
const snapshot = JSON.parse(
  await readFile(new URL("../src/data/photos/snapshot.json", import.meta.url), "utf8"),
);
const { default: curation } = await import("../src/data/photos/curation.ts");

await mkdir(dirname(out), { recursive: true });
await writeFile(out, JSON.stringify({ photos: snapshot, ...curation }, null, 2) + "\n");
console.log(`Wrote ${snapshot.length} photos and ${curation.collections.length} collections to ${out}`);
