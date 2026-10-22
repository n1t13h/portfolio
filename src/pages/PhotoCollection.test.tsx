import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, it, expect } from "vitest";
import { pastSkipGrace } from "@/test/timing";
import { mockMatchMedia, renderAt } from "@/test/utils";

it("renders title, facts and numbered chapters", async () => {
  renderAt("/photos/ujjain-omkareshwar-indore");
  expect(await screen.findByRole("heading", { level: 1, name: "Ujjain · Omkareshwar · Indore" })).toBeInTheDocument();
  expect(screen.getByText("Sony ZV-E10")).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual(["Ujjain", "Omkareshwar", "Indore, Rajwada & Sarafa", "Indore Zoo"]);
});

it("shows a not-found state for an unknown slug", async () => {
  renderAt("/photos/nope");
  expect(await screen.findByText(/collection not found/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /all collections/i })).toHaveAttribute("href", "/photos");
});

it("links to the next collection, wrapping to the first", async () => {
  renderAt("/photos/elsewhere");
  expect(await screen.findByRole("link", { name: /next collection/i })).toHaveAttribute("href", "/photos/ujjain-omkareshwar-indore");
});

describe("collection intro", () => {
  afterEach(() => {
    document.body.style.overflow = "";
  });

  it("plays when a collection opens, showing that collection's name", async () => {
    renderAt("/photos/mumbai");
    expect(await screen.findByTestId("collection-intro")).toHaveTextContent("Mumbai");
  });

  it("plays when opened by clicking through from /photos, not only on reload", async () => {
    renderAt("/photos");
    await userEvent.click(await screen.findByRole("link", { name: /mumbai/i }));
    const intro = await screen.findByTestId("collection-intro");
    expect(intro).toHaveTextContent("Mumbai");
    // (The same-click skip race needs a real browser click; it is covered by the grace-period test
    // in CollectionIntro.test.tsx.)
    expect(document.body.style.overflow).toBe("hidden");
    expect(intro.style.visibility).not.toBe("hidden");
  });

  it("plays again for the next collection", async () => {
    renderAt("/photos/mumbai");
    await screen.findByTestId("collection-intro");
    await pastSkipGrace();
    await userEvent.keyboard("a");
    await userEvent.click(await screen.findByRole("link", { name: /next collection/i }));
    await waitFor(() => expect(screen.getByTestId("collection-intro")).toHaveTextContent("Elsewhere"));
  });

  it("is skipped for a shared ?photo= link", async () => {
    renderAt("/photos/mumbai?photo=vZKi5-9C69I");
    await screen.findByRole("heading", { level: 1, name: "Mumbai" });
    expect(screen.queryByTestId("collection-intro")).toBeNull();
  });

  it("is skipped under reduced motion", async () => {
    mockMatchMedia("(prefers-reduced-motion: reduce)", true);
    renderAt("/photos/mumbai");
    await screen.findByRole("heading", { level: 1, name: "Mumbai" });
    expect(screen.queryByTestId("collection-intro")).toBeNull();
  });

  it("does not replay when the lightbox opens and closes", async () => {
    renderAt("/photos/mumbai");
    await screen.findByTestId("collection-intro");
    await pastSkipGrace();
    await userEvent.keyboard("a");
    await waitFor(() => expect(screen.queryByTestId("collection-intro")).toBeNull(), { timeout: 2000 });
    await userEvent.click((await screen.findAllByRole("button", { name: /^open /i }))[0]);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByTestId("collection-intro")).toBeNull();
  });
});
