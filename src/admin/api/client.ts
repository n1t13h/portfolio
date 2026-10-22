import type {
  AdminChapter,
  AdminCollection,
  AdminPhoto,
  CollectionInput,
  LoginInput,
  SyncStatus,
  UploadTicket,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function defaultApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_URL as string | undefined;
  if (configured) return configured.replace(/\/$/, "");
  return import.meta.env.DEV ? "http://localhost:8000" : "https://api.ntshptl.in";
}

interface Options {
  baseUrl?: string;
  /** The secret path segment from the page URL; the server only answers under /a/<prefix>. */
  prefix: string;
  fetch?: typeof fetch;
  /** Called when a request other than login/me comes back 401, e.g. the session expired. */
  onUnauthorized?: () => void;
}

/** FastAPI sends {detail: "text"} or, for validation errors, {detail: [{loc, msg}]}. */
function messageFrom(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => {
        const field = (d.loc ?? []).filter((p) => p !== "body").join(".");
        return field ? `${field}: ${d.msg}` : String(d.msg);
      })
      .join("; ");
  }
  return `Request failed (${status})`;
}

export type AdminApi = ReturnType<typeof createAdminApi>;

export function createAdminApi({
  baseUrl = defaultApiBaseUrl(),
  prefix,
  fetch: fetchImpl,
  onUnauthorized,
}: Options) {
  const root = `${baseUrl}/a/${prefix}`;
  const doFetch = (...args: Parameters<typeof fetch>) => (fetchImpl ?? fetch)(...args);

  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { "X-CSRF": "1" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await doFetch(`${root}${path}`, {
      method,
      headers,
      credentials: "include",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      if (response.status === 401 && !path.startsWith("/auth/")) onUnauthorized?.();
      const parsed = await response.json().catch(() => null);
      throw new ApiError(response.status, messageFrom(parsed, response.status));
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  const get = <T>(path: string) => request<T>("GET", path);
  const post = <T>(path: string, body?: unknown) => request<T>("POST", path, body);
  const put = <T>(path: string, body?: unknown) => request<T>("PUT", path, body);
  const patch = <T>(path: string, body: unknown) => request<T>("PATCH", path, body);
  const del = (path: string) => request<void>("DELETE", path);

  return {
    // session
    me: () => get<{ username: string }>("/auth/me"),
    login: (input: LoginInput) => post<{ username: string }>("/auth/login", input),
    logout: () => post<void>("/auth/logout"),

    // photos
    listPhotos: () => get<AdminPhoto[]>("/photos"),
    requestUpload: () => post<UploadTicket>("/photos/upload-url"),
    confirmUpload: (photoId: string) => post<AdminPhoto>(`/photos/${photoId}/confirm`),
    updatePhoto: (id: string, changes: { title?: string; place?: string | null }) =>
      patch<AdminPhoto>(`/photos/${id}`, changes),
    publishPhoto: (id: string) => post<AdminPhoto>(`/photos/${id}/publish`),
    unpublishPhoto: (id: string) => post<AdminPhoto>(`/photos/${id}/unpublish`),
    setAllowDownload: (id: string, allow: boolean) =>
      put<AdminPhoto>(`/photos/${id}/allow-download`, { allow }),
    deletePhoto: (id: string) => del(`/photos/${id}`),
    reorderPhotos: (ids: string[]) => put<void>("/photos/order", { ids }),

    // collections
    listCollections: () => get<AdminCollection[]>("/collections"),
    createCollection: (input: CollectionInput) => post<AdminCollection>("/collections", input),
    updateCollection: (id: string, changes: Partial<CollectionInput>) =>
      patch<AdminCollection>(`/collections/${id}`, changes),
    deleteCollection: (id: string) => del(`/collections/${id}`),
    publishCollection: (id: string) => post<AdminCollection>(`/collections/${id}/publish`),
    unpublishCollection: (id: string) => post<AdminCollection>(`/collections/${id}/unpublish`),
    reorderCollections: (ids: string[]) => put<void>("/collections/order", { ids }),
    setCovers: (id: string, photoIds: string[]) =>
      put<AdminCollection>(`/collections/${id}/covers`, { photoIds }),

    // chapters
    createChapter: (collectionId: string, input: { title?: string; note?: string }) =>
      post<AdminChapter>(`/collections/${collectionId}/chapters`, input),
    updateChapter: (id: string, changes: { title?: string; note?: string }) =>
      patch<AdminChapter>(`/chapters/${id}`, changes),
    deleteChapter: (id: string) => del(`/chapters/${id}`),
    reorderChapters: (collectionId: string, ids: string[]) =>
      put<void>(`/collections/${collectionId}/chapters/order`, { ids }),
    assignPhotos: (chapterId: string, photoIds: string[]) =>
      post<AdminChapter>(`/chapters/${chapterId}/photos`, { photoIds }),
    removePhoto: (chapterId: string, photoId: string) =>
      del(`/chapters/${chapterId}/photos/${photoId}`),
    reorderChapterPhotos: (chapterId: string, ids: string[]) =>
      put<void>(`/chapters/${chapterId}/photos/order`, { ids }),

    // sync
    syncStatus: () => get<SyncStatus>("/sync/status"),
    startSync: () => post<{ status: string }>("/sync"),
    startFullSync: () => post<{ status: string }>("/sync/full"),
  };
}
