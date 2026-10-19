import type { Photo, ResolvedCollection } from "@/data/photos";
import { FLOAT_COUNT } from "@/components/intro/floats";

const WIN_COUNT = 5;

/** "Ujjain · Omkareshwar · Indore" → the window opens after "Ujjain". */
export function splitTitle(title: string): { before: string; after: string } {
  const [first, ...rest] = title.split(" · ");
  return { before: first, after: rest.join(" · ") };
}

/**
 * Window photos are the collection's covers; floating tiles are spread evenly across the
 * remaining frames so they don't all come from the first chapter, topped up with the
 * window photos when a collection is small.
 */
export function pickIntroPhotos(c: ResolvedCollection): { floatPhotos: Photo[]; windowPhotos: Photo[] } {
  const windowPhotos = (c.covers.length ? c.covers : c.photos).slice(0, WIN_COUNT);
  const taken = new Set(windowPhotos.map((p) => p.id));
  const rest = c.photos.filter((p) => !taken.has(p.id));
  const spread =
    rest.length > FLOAT_COUNT
      ? Array.from({ length: FLOAT_COUNT }, (_, i) => rest[Math.floor((i * rest.length) / FLOAT_COUNT)])
      : rest;
  return { floatPhotos: [...spread, ...windowPhotos].slice(0, FLOAT_COUNT), windowPhotos };
}
