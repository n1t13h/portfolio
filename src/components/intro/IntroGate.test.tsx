import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { INTRO_KEY } from "./session";
import { DEV_FLOAT_TILES, DEV_WINDOW_TILES } from "./devTileSets";
import { pastSkipGrace } from "@/test/timing";
import { mockMatchMedia, renderAt } from "@/test/utils";

const REDUCED = "(prefers-reduced-motion: reduce)";

afterEach(() => {
  document.body.style.overflow = "";
});

describe("developer tiles", () => {
  it("cover the named topics, with a tile for every floating slot", () => {
    expect(DEV_FLOAT_TILES).toHaveLength(9);
    expect(DEV_WINDOW_TILES.length).toBeGreaterThanOrEqual(5);
  });
});

describe("?intro=developer", () => {
  it("plays the developer intro with tech tiles instead of photos", async () => {
    sessionStorage.removeItem(INTRO_KEY);
    renderAt("/?intro=developer");
    const intro = await screen.findByTestId("intro-developer");
    for (const topic of ["temporal", "agentic ai", "web3", "python", "microservices"]) {
      expect(intro).toHaveTextContent(topic);
    }
    expect(intro.querySelector("img")).toBeNull();
    expect(intro).toHaveTextContent("nitish");
    expect(intro).toHaveTextContent("patel");
  });

  it("replaces the default photo intro, even when it hasn't played this session", async () => {
    sessionStorage.removeItem(INTRO_KEY);
    renderAt("/?intro=developer");
    await screen.findByTestId("intro-developer");
    expect(screen.queryByTestId("intro")).toBeNull();
  });

  it("plays even if the default intro already played, and marks the session when skipped", async () => {
    sessionStorage.setItem(INTRO_KEY, "1");
    renderAt("/?intro=developer");
    await screen.findByTestId("intro-developer");
    sessionStorage.removeItem(INTRO_KEY);
    await act(pastSkipGrace);
    await userEvent.keyboard("a");
    expect(sessionStorage.getItem(INTRO_KEY)).toBe("1");
  });

  it("is skipped under reduced motion, without redirecting", async () => {
    mockMatchMedia(REDUCED, true);
    renderAt("/?intro=developer");
    await screen.findByTestId("page-home");
    expect(screen.queryByTestId("intro-developer")).toBeNull();
    expect(window.location.pathname).toBe("/");
  });
});

describe("?intro=photos", () => {
  it("plays the photo intro and opens the photography page", async () => {
    sessionStorage.removeItem(INTRO_KEY);
    renderAt("/?intro=photos");
    expect(await screen.findByTestId("intro")).toHaveTextContent("nitish");
    await screen.findByTestId("page-photos");
    expect(window.location.pathname).toBe("/photos");
    expect(window.location.search).toBe("");
    expect(screen.queryByTestId("page-home")).toBeNull();
  });

  it("still opens the photography page under reduced motion, without the intro", async () => {
    mockMatchMedia(REDUCED, true);
    renderAt("/?intro=photos");
    await screen.findByTestId("page-photos");
    expect(window.location.pathname).toBe("/photos");
    expect(screen.queryByTestId("intro")).toBeNull();
  });

  it("leaves a deeper photography URL where it is", async () => {
    renderAt("/photos/mumbai?intro=photos");
    await screen.findByTestId("page-photo-collection");
    expect(window.location.pathname).toBe("/photos/mumbai");
  });

  it("does not hijack later navigation", async () => {
    renderAt("/?intro=photos");
    await screen.findByTestId("page-photos");
    await userEvent.click(await screen.findByRole("link", { name: /mumbai/i }));
    await waitFor(() => expect(window.location.pathname).toBe("/photos/mumbai"));
  });
});

describe("unknown ?intro= value", () => {
  it("falls back to the default behaviour", async () => {
    sessionStorage.removeItem(INTRO_KEY);
    renderAt("/?intro=wedding");
    expect(await screen.findByTestId("intro-developer")).toBeInTheDocument();
    expect(screen.queryByTestId("intro")).toBeNull();
    expect(window.location.pathname).toBe("/");
  });
});

describe("collection intro", () => {
  it("steps aside when an explicit intro variant is playing", async () => {
    renderAt("/photos/mumbai?intro=developer");
    await screen.findByRole("heading", { level: 1, name: "Mumbai" });
    expect(screen.queryByTestId("collection-intro")).toBeNull();
    expect(screen.getByTestId("intro-developer")).toBeInTheDocument();
  });
});
