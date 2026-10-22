import type { AdminPhoto, UploadTicket } from "../api/types";

export interface UploadApi {
  requestUpload(): Promise<UploadTicket>;
  confirmUpload(photoId: string): Promise<AdminPhoto>;
}

export type UploadResult =
  | { name: string; ok: true; photoId: string }
  | { name: string; ok: false; error: string };

export interface UploadProgress {
  name: string;
  /** 0..1 of the file sent to storage; the server-side processing step comes after. */
  fraction: number;
}

type Put = (url: string, file: File, onProgress: (fraction: number) => void) => Promise<void>;

interface Options {
  put?: Put;
  concurrency?: number;
  onProgress?: (progress: UploadProgress) => void;
}

const isJpeg = (file: File) => file.type === "image/jpeg" || /\.jpe?g$/i.test(file.name);

/** PUT with progress events (fetch cannot report upload progress). */
export const putWithProgress: Put = (url, file, onProgress) =>
  new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", "image/jpeg");
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve()
        : reject(new Error(`Storage refused the upload (${xhr.status})`));
    xhr.onerror = () => reject(new Error("Could not reach storage"));
    xhr.send(file);
  });

const reasonOf = (e: unknown) => (e instanceof Error ? e.message : String(e));

/**
 * Upload photos: ask the API for a link, send the file straight to storage, then ask the
 * API to process it. One failure never stops the others.
 */
export async function uploadPhotos(
  api: UploadApi,
  files: File[],
  { put = putWithProgress, concurrency = 2, onProgress }: Options = {},
): Promise<UploadResult[]> {
  const results: UploadResult[] = new Array(files.length);
  let next = 0;

  async function uploadOne(file: File): Promise<UploadResult> {
    if (!isJpeg(file)) return { name: file.name, ok: false, error: "Only JPEG photos can be uploaded." };
    try {
      const ticket = await api.requestUpload();
      await put(ticket.putUrl, file, (fraction) => onProgress?.({ name: file.name, fraction }));
      await api.confirmUpload(ticket.photoId);
      return { name: file.name, ok: true, photoId: ticket.photoId };
    } catch (e) {
      return { name: file.name, ok: false, error: reasonOf(e) };
    }
  }

  async function worker() {
    while (next < files.length) {
      const index = next++;
      results[index] = await uploadOne(files[index]);
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrency, files.length) }, worker));
  return results;
}
