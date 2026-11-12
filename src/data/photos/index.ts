// Photos and collections come from the API at build time (scripts/fetch-catalog.mjs writes
// catalog.json; tests alias it to src/test/fixtures/catalog.json). Ordering, drafts and
// exclusions are already applied by the API.
import catalogJson from "@/data/photos/catalog.json";
import type { Catalog, Photo, ResolvedCollection } from "./types";

export type * from "./types";
export { formatPhotoMeta } from "./format";

const catalog = catalogJson as Catalog;

export async function getPhotos(): Promise<Photo[]> {
  return catalog.photos;
}

export async function getCollections(): Promise<ResolvedCollection[]> {
  return catalog.collections;
}

export async function getCollection(slug: string): Promise<ResolvedCollection | null> {
  return catalog.collections.find((c) => c.slug === slug) ?? null;
}

export function collectionOf(
  photoId: string,
  collections: ResolvedCollection[],
): ResolvedCollection | undefined {
  return collections.find((c) => c.photos.some((p) => p.id === photoId));
}

/** The id used in ?photo= links: the Unsplash id where there is one, so links keep their form. */
export function photoKey(photo: Photo): string {
  return photo.unsplashId ?? photo.id;
}

/** Index of the photo a ?photo= value points at (its id or its Unsplash id), else -1. */
export function findPhoto(photos: Photo[], key: string): number {
  return photos.findIndex((p) => p.id === key || p.unsplashId === key);
}
