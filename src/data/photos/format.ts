import type { Photo } from "./types";

export function formatPhotoMeta(p: Photo): string {
  const e = p.exif;
  return [
    p.place,
    e?.focalLength !== undefined ? `${e.focalLength}mm` : undefined,
    e?.aperture !== undefined ? `ƒ/${e.aperture}` : undefined,
    e?.shutter !== undefined ? `${e.shutter}s` : undefined,
    e?.iso !== undefined ? `ISO ${e.iso}` : undefined,
  ]
    .filter((part): part is string => Boolean(part))
    .join(" · ");
}
