import { describe, it, expect } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderAt } from "@/test/utils";
import { getPhotos } from "@/data/photos";

const pad = (n: number) => String(n).padStart(2, "0");
const currentCounter = () => screen.getByTestId("lightbox-counter").textContent ?? "";

describe("Lightbox", () => {
  it("opens from ?photo= and shows caption + metadata", async () => {
    renderAt("/photos?photo=I5lzt9e4WMY");
    expect(await screen.findByRole("dialog")).toHaveTextContent("Performer creating a fiery hoop with fire");
    expect(screen.getByRole("dialog")).toHaveTextContent("ƒ/36");
  });

  it("ignores an unknown ?photo= id", async () => {
    renderAt("/photos?photo=nope");
    await screen.findAllByTestId("sheet-photo");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("wraps around with arrow keys and closes on Escape, restoring scroll", async () => {
    const photos = await getPhotos();
    const total = photos.length;
    renderAt(`/photos?photo=${photos[0].id}`);
    await screen.findByRole("dialog");
    expect(document.body.style.overflow).toBe("hidden");
    expect(currentCounter()).toBe(`${pad(1)} / ${pad(total)}`);
    await userEvent.keyboard("{ArrowLeft}");
    expect(currentCounter()).toBe(`${pad(total)} / ${pad(total)}`);
    await userEvent.keyboard("{ArrowRight}");
    expect(currentCounter()).toBe(`${pad(1)} / ${pad(total)}`);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.body.style.overflow).toBe("");
  });

  it("moves focus to Close when opened", async () => {
    renderAt("/photos?photo=I5lzt9e4WMY");
    const dialog = await screen.findByRole("dialog");
    const close = within(dialog).getByRole("button", { name: /close/i });
    expect(close).toHaveFocus();
  });

  it("updates the URL when navigating and closes via the backdrop", async () => {
    renderAt("/photos?photo=I5lzt9e4WMY");
    await screen.findByRole("dialog");
    await userEvent.click(screen.getByRole("button", { name: /next photo/i }));
    expect(window.location.search).not.toContain("I5lzt9e4WMY");
    await userEvent.click(screen.getByTestId("lightbox-backdrop"));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(window.location.search).toBe("");
  });

  it("restores body scroll when unmounted while open", async () => {
    const { unmount } = renderAt("/photos?photo=I5lzt9e4WMY");
    await screen.findByRole("dialog");
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).toBe("");
  });

  it("links to the photo's collection essay", async () => {
    renderAt("/photos?photo=I5lzt9e4WMY");
    expect(
      await screen.findByRole("link", { name: /from ujjain · omkareshwar · indore/i }),
    ).toHaveAttribute("href", "/photos/ujjain-omkareshwar-indore");
  });
  it("fades each new photo in once, without flashing it at full opacity first", async () => {
    renderAt("/photos?photo=I5lzt9e4WMY");
    const dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(within(dialog).getByRole("img")).toHaveClass("opacity-100"));
    // A bare `opacity-100` (not the `motion-reduce:` variant) means fully visible.
    const visible = (cls?: string | null) => /(^|\s)opacity-100(\s|$)/.test(cls ?? "");
    const flashes: string[] = [];
    const observer = new MutationObserver((records) =>
      records.forEach((r) => {
        if ((r.target as Element).tagName === "IMG" && visible(r.oldValue)) {
          flashes.push(r.oldValue!);
        }
      }),
    );
    observer.observe(dialog, { subtree: true, attributes: true, attributeFilter: ["class"], attributeOldValue: true });
    await userEvent.click(screen.getByRole("button", { name: /next photo/i }));
    const next = within(dialog).getByRole("img");
    expect(next).not.toHaveAttribute("alt", "Performer creating a fiery hoop with fire");
    await waitFor(() => expect(next).toHaveClass("opacity-100"));
    observer.takeRecords().forEach((r) => visible(r.oldValue) && flashes.push(r.oldValue!));
    observer.disconnect();
    expect(flashes).toEqual([]);
  });
});
