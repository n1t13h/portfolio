export type Exif = {
  camera?: string;
  focalLength?: number;
  aperture?: number;
  shutter?: string;
  iso?: number;
};

export type Photo = {
  id: string;
  pid: string;
  aspectRatio: number;
  title: string;
  place?: string;
  exif?: Exif;
  unsplashUrl: string;
};

export type Chapter = { title: string; note: string; photoIds: string[] };

export type Collection = {
  slug: string;
  title: string;
  place: string;
  year: string;
  intro: string;
  coverIds: string[];
  chapters: Chapter[];
};

export type ResolvedChapter = Omit<Chapter, "photoIds"> & { photos: Photo[] };

export type ResolvedCollection = Omit<Collection, "chapters" | "coverIds"> & {
  covers: Photo[];
  chapters: ResolvedChapter[];
  photos: Photo[];
};

export type Curation = {
  order: string[];
  excluded: string[];
  collections: Collection[];
};
