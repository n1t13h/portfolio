import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getCollections } from "@/data/photos";
import { FLOAT_COUNT } from "@/components/intro/floats";
import { pastSkipGrace } from "@/test/timing";
import { CollectionIntro } from "./CollectionIntro";
import { pickIntroPhotos, splitTitle } from "./introPhotos";

describe("splitTitle", () => {
  it("opens the window after the first part of a multi-part title", () => {
    expect(splitTitle("Ujjain · Omkareshwar · Indore")).toEqual({ before: "Ujjain", after: "Omkareshwar · Indore" });
  });
  it("puts the window at the end of a single-word title", () => {
    expect(splitTitle("Mumbai")).toEqual({ before: "Mumbai", after: "" });
  });
});

describe("pickIntroPhotos", () => {
  it("uses the covers for the window and only the collection's own photos for the tiles", async () => {
    for (const c of await getCollections()) {
      const { floatPhotos, windowPhotos } = pickIntroPhotos(c);
      const own = new Set(c.photos.map((p) => p.id));
      expect(windowPhotos.map((p) => p.id)).toEqual(c.covers.slice(0, 5).map((p) => p.id));
      expect(floatPhotos.length).toBeGreaterThan(0);
      expect(floatPhotos.length).toBeLessThanOrEqual(FLOAT_COUNT);
      floatPhotos.forEach((p) => expect(own.has(p.id)).toBe(true));
      expect(new Set(floatPhotos.map((p) => p.id)).size).toBe(floatPhotos.length);
    }
  });

  it("spreads tiles across the whole collection, not just its first frames", async () => {
    const c = (await getCollections()).find((x) => x.slug === "ujjain-omkareshwar-indore")!;
    const { floatPhotos } = pickIntroPhotos(c);
    const firstChapter = new Set(c.chapters[0].photos.map((p) => p.id));
    expect(floatPhotos.some((p) => !firstChapter.has(p.id))).toBe(true);
    expect(floatPhotos.filter((p) => firstChapter.has(p.id)).length).toBeLessThan(floatPhotos.length);
  });
});

describe("<CollectionIntro />", () => {
  afterEach(() => {
    vi.useRealTimers();
    document.body.style.overflow = "";
  });

  it("shows the collection's name and locks body scroll", async () => {
    const [c] = await getCollections();
    render(<CollectionIntro collection={c} />);
    expect(screen.getByTestId("collection-intro")).toHaveTextContent("Ujjain");
    expect(screen.getByTestId("collection-intro")).toHaveTextContent("Omkareshwar · Indore");
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("skips on a key press and releases scroll, without touching the site-intro session flag", async () => {
    const [c] = await getCollections();
    sessionStorage.removeItem("intro-played");
    render(<CollectionIntro collection={c} />);
    await pastSkipGrace();
    await userEvent.keyboard("a");
    expect(document.body.style.overflow).toBe("");
    expect(sessionStorage.getItem("intro-played")).toBeNull();
  });

  it("removes itself shortly after it ends", async () => {
    vi.useFakeTimers();
    const [c] = await getCollections();
    render(<CollectionIntro collection={c} />);
    act(() => void vi.advanceTimersByTime(2600)); // intro ends, fade begins
    act(() => void vi.advanceTimersByTime(700)); // fade completes, overlay unmounts
    expect(screen.queryByTestId("collection-intro")).toBeNull();
    expect(document.body.style.overflow).toBe("");
  });

  it("ignores the click that opened it, then skips on later input", async () => {
    // The click that navigates to a collection is still bubbling when the intro mounts; a real
    // browser delivers it to the intro's window listeners, which used to skip it instantly.
    vi.useFakeTimers();
    const [c] = await getCollections();
    render(<CollectionIntro collection={c} />);
    fireEvent.click(window);
    fireEvent.keyDown(window, { key: "Enter" });
    expect(document.body.style.overflow).toBe("hidden");
    expect(screen.getByTestId("collection-intro").style.visibility).not.toBe("hidden");

    act(() => void vi.advanceTimersByTime(300));
    fireEvent.click(window);
    expect(document.body.style.overflow).toBe("");
    expect(screen.getByTestId("collection-intro").style.visibility).toBe("hidden");
  });
});
