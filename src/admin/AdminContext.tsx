import { createContext, useContext } from "react";
import type { AdminApi } from "./api/client";

interface AdminContextValue {
  api: AdminApi;
  /** The secret path segment, used to build links inside the admin. */
  prefix: string;
  username: string;
  signOut: () => Promise<void>;
}

export const AdminContext = createContext<AdminContextValue | null>(null);

export function useAdmin(): AdminContextValue {
  const value = useContext(AdminContext);
  if (!value) throw new Error("useAdmin must be used inside <AdminApp>");
  return value;
}
