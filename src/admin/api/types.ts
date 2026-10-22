// Shapes returned by the backend's admin API (camelCase on the wire).

export type Status = "draft" | "published";

export interface AdminPhoto {
  id: string;
  title: string;
  place: string | null;
  aspectRatio: number;
  exif: { camera?: string; focal_length?: number; aperture?: number; shutter?: string; iso?: number };
  takenAt: string | null;
  status: Status;
  allowDownload: boolean;
  sortPosition: number;
  chapterId: string | null;
  unsplashId: string | null;
  /** long edge in px -> public CDN URL */
  variants: Record<string, string>;
  createdAt: string;
}

export interface AdminChapter {
  id: string;
  collectionId: string;
  title: string;
  note: string;
  position: number;
  photoIds: string[];
}

export interface AdminCollection {
  id: string;
  slug: string;
  title: string;
  place: string;
  year: string;
  intro: string;
  status: Status;
  sortPosition: number;
  coverPhotoIds: string[];
  chapters: AdminChapter[];
}

export interface UploadTicket {
  photoId: string;
  putUrl: string;
  key: string;
}

export interface SyncStatus {
  running: boolean;
  lastStartedAt: string | null;
  lastFinishedAt: string | null;
  lastImported: number;
  lastError: string | null;
  rateLimitRemaining: number | null;
  pending: number;
}

export interface LoginInput {
  username: string;
  password: string;
  code: string;
}

export interface CollectionInput {
  slug: string;
  title: string;
  place?: string;
  year?: string;
  intro?: string;
}
