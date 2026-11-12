import { afterEach, expect, it, vi } from "vitest";
import { apiBase } from "./api";

afterEach(() => vi.unstubAllEnvs());

it("uses VITE_API_URL when it is set, without a trailing slash", () => {
  vi.stubEnv("VITE_API_URL", "https://api.example.test/");
  expect(apiBase()).toBe("https://api.example.test");
});

it("falls back to the local API in development", () => {
  vi.stubEnv("VITE_API_URL", "");
  expect(apiBase()).toBe("http://localhost:8000");
});
