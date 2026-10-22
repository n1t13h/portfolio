import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fakeBackend, json, noContent, renderAdmin, route } from "./test/harness";

afterEach(() => vi.unstubAllGlobals());

const signedIn = route("GET", "/auth/me", json({ username: "nitish" }));
const signedOut = route("GET", "/auth/me", json({ detail: "not authenticated" }, 401));
const empty = [
  route("GET", "/photos", json([])),
  route("GET", "/collections", json([])),
  route("GET", "/sync/status", json({ running: false, lastImported: 0, pending: 0 })),
];

describe("admin shell", () => {
  it("shows a plain not-found page when the secret path is wrong", async () => {
    fakeBackend(route("GET", "/auth/me", json({ detail: "Not Found" }, 404)));
    renderAdmin("/a/wrong-guess/photos");
    expect(await screen.findByText(/page not found/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
  });

  it("asks for password and a 2FA code when there is no session", async () => {
    fakeBackend(signedOut);
    renderAdmin();
    expect(await screen.findByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toHaveAttribute("type", "password");
    expect(screen.getByLabelText(/code/i)).toBeInTheDocument();
  });

  it("signs in, then shows the admin", async () => {
    let signedInNow = false;
    const { calls } = fakeBackend(
      route("POST", "/auth/login", () => {
        signedInNow = true;
        return json({ username: "nitish" });
      }),
      (req) => (req.path === "/auth/me" ? (signedInNow ? json({ username: "nitish" }) : json({ detail: "x" }, 401)) : undefined),
      ...empty,
    );
    renderAdmin();
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText(/username/i), "nitish");
    await user.type(screen.getByLabelText(/password/i), "hunter2");
    await user.type(screen.getByLabelText(/code/i), "123456");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("link", { name: /photos/i })).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/auth/login")?.body).toEqual({
      username: "nitish",
      password: "hunter2",
      code: "123456",
    });
  });

  it("says the details were wrong without saying which part", async () => {
    fakeBackend(signedOut, route("POST", "/auth/login", json({ detail: "invalid credentials" }, 401)));
    renderAdmin();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/username/i), "nitish");
    await user.type(screen.getByLabelText(/password/i), "bad");
    await user.type(screen.getByLabelText(/code/i), "000000");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/didn't work/i);
  });

  it("tells you when you are locked out", async () => {
    fakeBackend(signedOut, route("POST", "/auth/login", json({ detail: "too many attempts" }, 429)));
    renderAdmin();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/username/i), "nitish");
    await user.type(screen.getByLabelText(/password/i), "x");
    await user.type(screen.getByLabelText(/code/i), "000000");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/too many attempts.*15 minutes/i);
  });

  it("explains when the API cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    renderAdmin();
    expect(await screen.findByText(/can.t reach the api/i)).toBeInTheDocument();
  });

  it("has Photos, Collections and Sync tabs and keeps search engines out", async () => {
    fakeBackend(signedIn, ...empty);
    renderAdmin();
    expect(await screen.findByRole("link", { name: "Photos" })).toHaveAttribute("href", "/a/test-prefix/photos");
    expect(screen.getByRole("link", { name: "Collections" })).toHaveAttribute("href", "/a/test-prefix/collections");
    expect(screen.getByRole("link", { name: "Sync" })).toHaveAttribute("href", "/a/test-prefix/sync");
    expect(document.querySelector('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  });

  it("sends an empty admin path to the photos tab", async () => {
    fakeBackend(signedIn, ...empty);
    renderAdmin("/a/test-prefix");
    expect(await screen.findByRole("heading", { name: "Photos" })).toBeInTheDocument();
  });

  it("signs out and goes back to the login form", async () => {
    let out = false;
    fakeBackend(
      route("POST", "/auth/logout", () => {
        out = true;
        return noContent();
      }),
      (req) => (req.path === "/auth/me" ? (out ? json({ detail: "x" }, 401) : json({ username: "nitish" })) : undefined),
      ...empty,
    );
    renderAdmin();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /sign out/i }));

    await waitFor(() => expect(screen.getByLabelText(/username/i)).toBeInTheDocument());
  });
});
