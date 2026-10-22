import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import AdminApp from "../AdminApp";

export type Handler = (request: { method: string; path: string; body: unknown }) => Response | undefined;

export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
export const noContent = () => new Response(null, { status: 204 });

/**
 * A tiny fake backend: every request is offered to the handlers in order; the first to
 * return a Response wins. `calls` records what the UI sent, for assertions.
 */
export function fakeBackend(...handlers: Handler[]) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(url).pathname.replace(/^\/a\/[^/]+/, "");
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    const request = { method: init?.method ?? "GET", path, body };
    calls.push(request);
    for (const handler of handlers) {
      const response = handler(request);
      if (response) return response;
    }
    return json({ detail: `unhandled ${request.method} ${path}` }, 500);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

export const route =
  (method: string, path: string, respond: Response | ((body: unknown) => Response)): Handler =>
  (req) =>
    req.method === method && req.path === path
      ? typeof respond === "function"
        ? respond(req.body)
        : respond.clone()
      : undefined;

export function renderAdmin(path = "/a/test-prefix/photos") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/a/:prefix/*" element={<AdminApp />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
