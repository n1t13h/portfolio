import type { Photo } from "@/data/photos";

/**
 * Each CDN size with its real pixel width, narrowest first. Variant keys are the long edge,
 * which for a portrait photo is the height, so the width is the edge scaled by the aspect ratio.
 */
const sizes = (photo: Photo): [number, string][] =>
  Object.entries(photo.variants)
    .map(([edge, url]): [number, string] => [
      Math.round(Number(edge) * Math.min(1, photo.aspectRatio)),
      url,
    ])
    .sort(([a], [b]) => a - b);

/** The narrowest CDN size at least `width` px wide, else the widest there is. */
export function photoSrc(photo: Photo, width: number): string {
  const all = sizes(photo);
  return (all.find(([w]) => w >= width) ?? all[all.length - 1])[1];
}

/** Every CDN size as a srcset with its real width, narrowest first. */
export function photoSrcSet(photo: Photo): string {
  return sizes(photo)
    .map(([w, url]) => `${url} ${w}w`)
    .join(", ");
}
