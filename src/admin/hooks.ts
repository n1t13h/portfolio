import { useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAdmin } from "./AdminContext";

/** One place that knows the cache keys, so pages can refresh each other's data. */
export function useAdminKeys() {
  const { prefix } = useAdmin();
  return useMemo(
    () => ({
      photos: ["admin", prefix, "photos"] as const,
      collections: ["admin", prefix, "collections"] as const,
      sync: ["admin", prefix, "sync"] as const,
    }),
    [prefix],
  );
}

export function usePhotos() {
  const { api } = useAdmin();
  const keys = useAdminKeys();
  return useQuery({ queryKey: keys.photos, queryFn: api.listPhotos });
}

export function useCollections() {
  const { api } = useAdmin();
  const keys = useAdminKeys();
  return useQuery({ queryKey: keys.collections, queryFn: api.listCollections });
}

/**
 * Runs an admin action: on failure shows the server's reason, and either way re-reads photos
 * and collections (they reference each other: chapters hold photos, photos know their chapter).
 */
export function useAction() {
  const queryClient = useQueryClient();
  const keys = useAdminKeys();
  return useCallback(
    async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
      try {
        return await action();
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Something went wrong");
        return undefined;
      } finally {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: keys.photos }),
          queryClient.invalidateQueries({ queryKey: keys.collections }),
        ]);
      }
    },
    [queryClient, keys],
  );
}
