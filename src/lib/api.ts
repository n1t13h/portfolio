/** The API's base URL: VITE_API_URL if set, the local API in dev, else production. */
export function apiBase(): string {
  const configured = import.meta.env.VITE_API_URL as string | undefined;
  if (configured) return configured.replace(/\/$/, "");
  return import.meta.env.DEV ? "http://localhost:8000" : "https://api.ntshptl.in";
}
