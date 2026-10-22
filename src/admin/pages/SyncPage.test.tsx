import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SyncStatus } from "../api/types";
import { fakeBackend, json, renderAdmin, route } from "../test/harness";

afterEach(() => vi.unstubAllGlobals());

const idle: SyncStatus = {
  running: false,
  lastStartedAt: "2026-10-01T09:00:00Z",
  lastFinishedAt: "2026-10-01T09:02:00Z",
  lastImported: 3,
  lastError: null,
  rateLimitRemaining: 41,
  pending: 0,
};

function backend(status: SyncStatus, extra: ReturnType<typeof route>[] = []) {
  return fakeBackend(
    route("GET", "/auth/me", json({ username: "nitish" })),
    route("GET", "/sync/status", () => json(status)),
    route("GET", "/photos", json([])),
    route("GET", "/collections", json([])),
    ...extra,
  );
}

describe("sync page", () => {
  it("summarises the last run", async () => {
    backend(idle);
    renderAdmin("/a/test-prefix/sync");
    expect(await screen.findByText(/3 photos imported/i)).toBeInTheDocument();
    expect(screen.getByText(/41 requests left this hour/i)).toBeInTheDocument();
  });

  it("says plainly when nothing has ever run", async () => {
    backend({ ...idle, lastStartedAt: null, lastFinishedAt: null, lastImported: 0, rateLimitRemaining: null });
    renderAdmin("/a/test-prefix/sync");
    expect(await screen.findByText(/hasn.t run yet/i)).toBeInTheDocument();
  });

  it("shows what went wrong and what is still waiting", async () => {
    backend({ ...idle, lastError: "abc123: giving up after 3 failures", pending: 2 });
    renderAdmin("/a/test-prefix/sync");
    expect(await screen.findByRole("alert")).toHaveTextContent("abc123: giving up after 3 failures");
    expect(screen.getByText(/2 photos waiting for the next run/i)).toBeInTheDocument();
  });

  it("starts a sync and shows that it is running", async () => {
    let running = false;
    const { calls } = fakeBackend(
      route("GET", "/auth/me", json({ username: "nitish" })),
      route("POST", "/sync", () => {
        running = true;
        return json({ status: "started" }, 202);
      }),
      route("GET", "/sync/status", () => json({ ...idle, running })),
      route("GET", "/photos", json([])),
      route("GET", "/collections", json([])),
    );
    renderAdmin("/a/test-prefix/sync");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Sync now" }));

    await waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === "/sync")).toBe(true));
    expect(await screen.findByText(/sync is running/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sync now" })).toBeDisabled();
  });

  it("asks before a full resync, which walks every page", async () => {
    const { calls } = backend(idle, [route("POST", "/sync/full", json({ status: "started" }, 202))]);
    renderAdmin("/a/test-prefix/sync");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Full resync" }));
    expect(calls.some((c) => c.path === "/sync/full")).toBe(false);
    await user.click(await screen.findByRole("button", { name: "Start full resync" }));

    await waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === "/sync/full")).toBe(true));
  });
});
