import { useEffect, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import NotFound from "@/pages/NotFound";
import { AdminContext } from "./AdminContext";
import { AdminLayout } from "./AdminLayout";
import { LoginForm } from "./LoginForm";
import { ApiError, createAdminApi } from "./api/client";

/** Keep search engines away; the page is only reachable through its secret URL anyway. */
function useNoIndex() {
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex, nofollow";
    document.head.appendChild(meta);
    return () => meta.remove();
  }, []);
}

export default function AdminApp() {
  const { prefix = "" } = useParams();
  const queryClient = useQueryClient();
  const meKey = useMemo(() => ["admin", prefix, "me"], [prefix]);
  const api = useMemo(
    () =>
      createAdminApi({
        prefix,
        onUnauthorized: () => void queryClient.invalidateQueries({ queryKey: meKey }),
      }),
    [prefix, queryClient, meKey],
  );
  useNoIndex();

  const me = useQuery({ queryKey: meKey, queryFn: api.me, retry: false });

  if (me.isPending) {
    return <p className="p-8 text-[15px] text-[#6b6b6b]">Loading…</p>;
  }
  if (me.error instanceof ApiError && me.error.status === 404) {
    return <NotFound />; // wrong secret path: look like any other missing page
  }
  if (me.error instanceof ApiError && me.error.status === 401) {
    return <LoginForm api={api} onSignedIn={() => void queryClient.invalidateQueries({ queryKey: meKey })} />;
  }
  if (me.error || !me.data) {
    return (
      <main className="mx-auto max-w-[520px] px-6 pt-24">
        <p className="text-[20px] tracking-[-0.02em]">Can't reach the API.</p>
        <p className="mt-2 text-[15px] text-[#6b6b6b]">Is the backend running? {me.error?.message}</p>
        <Button className="mt-6" variant="outline" onClick={() => void me.refetch()}>
          Try again
        </Button>
      </main>
    );
  }

  async function signOut() {
    await api.logout().catch(() => {});
    // Forget the admin's data, but keep the session query so it re-checks and shows the login.
    queryClient.removeQueries({
      predicate: (q) => q.queryKey[0] === "admin" && q.queryKey[1] === prefix && q.queryKey[2] !== "me",
    });
    await queryClient.invalidateQueries({ queryKey: meKey });
  }

  return (
    <AdminContext.Provider value={{ api, prefix, username: me.data.username, signOut }}>
      <AdminLayout />
    </AdminContext.Provider>
  );
}
