export type Exif = {
  camera?: string;
  focalLength?: number;
  aperture?: number;
  shutter?: string;
  iso?: number;
};

/** A published photo, as written to catalog.json by scripts/fetch-catalog.mjs. */
export type Photo = {
  id: string;
  title: string;
  place?: string;
  aspectRatio: number;
  exif?: Exif;
  /** Long edge in px ("800", "1600", "2400") -> image URL on cdn.ntshptl.in. */
  variants: Record<string, string>;
  unsplashId?: string;
  unsplashUrl?: string;
  /** API path that redirects to the file; present only when downloads are allowed. */
  downloadUrl?: string;
};

export type ResolvedChapter = { title: string; note: string; photos: Photo[] };

export type ResolvedCollection = {
  slug: string;
  title: string;
  place: string;
  year: string;
  intro: string;
  covers: Photo[];
  chapters: ResolvedChapter[];
  photos: Photo[];
};

export type Catalog = { photos: Photo[]; collections: ResolvedCollection[] };
