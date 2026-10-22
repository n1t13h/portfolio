import { describe, expect, it, vi } from "vitest";
import { ApiError, createAdminApi } from "./client";

function setup(response: Response | (() => Response)) {
  const fetchMock = vi.fn(async () => (typeof response === "function" ? response() : response));
  const api = createAdminApi({
    baseUrl: "http://api.test",
    prefix: "secret-prefix",
    fetch: fetchMock as unknown as typeof fetch,
  });
  return { api, fetchMock };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("admin api client", () => {
  it("calls the secret path with the session cookie and the CSRF header", async () => {
    const { api, fetchMock } = setup(json({ username: "nitish" }));

    await api.me();

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/a/secret-prefix/auth/me");
    expect(init.credentials).toBe("include");
    expect((init.headers as Record<string, string>)["X-CSRF"]).toBe("1");
  });

  it("sends JSON bodies with the right method", async () => {
    const { api, fetchMock } = setup(json({ username: "nitish" }));

    await api.login({ username: "nitish", password: "pw", code: "123456" });

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/a/secret-prefix/auth/login");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({
      username: "nitish",
      password: "pw",
      code: "123456",
    });
  });

  it("returns undefined for 204 responses", async () => {
    const { api } = setup(new Response(null, { status: 204 }));
    await expect(api.logout()).resolves.toBeUndefined();
  });

  it("turns error responses into ApiError with status and the server's detail", async () => {
    const { api } = setup(() => json({ detail: "invalid credentials" }, 401));

    const error = await api.me().catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(401);
    expect(error.message).toBe("invalid credentials");
  });

  it("explains validation errors in words, not as [object Object]", async () => {
    const detail = [{ loc: ["body", "slug"], msg: "String should match pattern" }];
    const { api } = setup(() => json({ detail }, 422));

    const error = await api.createCollection({ slug: "Bad Slug", title: "x" }).catch((e) => e);

    expect(error.message).toContain("slug");
    expect(error.message).toContain("String should match pattern");
  });

  it("copes with a non-JSON error body", async () => {
    const { api } = setup(() => new Response("Bad gateway", { status: 502 }));
    const error = await api.me().catch((e) => e);
    expect(error.status).toBe(502);
    expect(error.message).toBe("Request failed (502)");
  });

  it("reorders with the ids in the body", async () => {
    const { api, fetchMock } = setup(new Response(null, { status: 204 }));

    await api.reorderPhotos(["b", "a"]);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/a/secret-prefix/photos/order");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({ ids: ["b", "a"] });
  });

  it("assigns photos to a chapter with camelCase field names", async () => {
    const { api, fetchMock } = setup(json({ id: "c1" }));

    await api.assignPhotos("c1", ["p1", "p2"]);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/a/secret-prefix/chapters/c1/photos");
    expect(JSON.parse(init.body as string)).toEqual({ photoIds: ["p1", "p2"] });
  });

  it("falls back to the default API address when none is configured", async () => {
    const { defaultApiBaseUrl } = await import("./client");
    expect(defaultApiBaseUrl()).toMatch(/^https?:\/\//);
  });
});

describe("expired sessions", () => {
  it("tells the app when a normal request is rejected as unauthenticated", async () => {
    const onUnauthorized = vi.fn();
    const api = createAdminApi({
      baseUrl: "http://api.test",
      prefix: "p",
      fetch: (async () => json({ detail: "not authenticated" }, 401)) as unknown as typeof fetch,
      onUnauthorized,
    });

    await api.listPhotos().catch(() => {});

    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("does not treat a failed login as an expired session", async () => {
    const onUnauthorized = vi.fn();
    const api = createAdminApi({
      baseUrl: "http://api.test",
      prefix: "p",
      fetch: (async () => json({ detail: "invalid credentials" }, 401)) as unknown as typeof fetch,
      onUnauthorized,
    });

    await api.login({ username: "a", password: "b", code: "c" }).catch(() => {});

    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
