import snapshotJson from "./snapshot.json";
import curation from "./curation";
import type { Curation, Photo, ResolvedCollection } from "./types";

export type * from "./types";
export { formatPhotoMeta } from "./format";

const snapshot = snapshotJson as Photo[];

export function orderPhotos(snap: Photo[], cur: Curation): Photo[] {
  const excluded = new Set(cur.excluded);
  const visible = snap.filter((p) => !excluded.has(p.id));
  const byId = new Map(visible.map((p) => [p.id, p]));
  const first = cur.order.flatMap((id) => {
    const p = byId.get(id);
    return p ? [p] : [];
  });
  const placed = new Set(first.map((p) => p.id));
  return [...first, ...visible.filter((p) => !placed.has(p.id))];
}

export function resolveCollections(snap: Photo[], cur: Curation): ResolvedCollection[] {
  const byId = new Map(snap.map((p) => [p.id, p]));
  const pick = (ids: string[], where: string): Photo[] =>
    ids.flatMap((id) => {
      const p = byId.get(id);
      if (!p) {
        console.warn(`Photo "${id}" referenced by ${where} is missing from the snapshot`);
        return [];
      }
      return [p];
    });

  return cur.collections.map(({ coverIds, chapters, ...rest }) => {
    const resolved = chapters.map(({ photoIds, ...ch }) => ({
      ...ch,
      photos: pick(photoIds, `${rest.slug}/${ch.title}`),
    }));
    return {
      ...rest,
      covers: pick(coverIds, `${rest.slug} covers`),
      chapters: resolved,
      photos: resolved.flatMap((c) => c.photos),
    };
  });
}

export async function getPhotos(): Promise<Photo[]> {
  return orderPhotos(snapshot, curation);
}

export async function getCollections(): Promise<ResolvedCollection[]> {
  return resolveCollections(snapshot, curation);
}

export async function getCollection(slug: string): Promise<ResolvedCollection | null> {
  return (await getCollections()).find((c) => c.slug === slug) ?? null;
}

export function collectionOf(
  photoId: string,
  collections: ResolvedCollection[],
): ResolvedCollection | undefined {
  return collections.find((c) => c.photos.some((p) => p.id === photoId));
}
