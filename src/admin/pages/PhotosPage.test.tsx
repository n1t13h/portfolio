import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AdminCollection, AdminPhoto } from "../api/types";
import { fakeBackend, json, noContent, renderAdmin, route } from "../test/harness";
import * as upload from "../lib/upload";

vi.mock("../lib/upload", async (original) => ({
  ...(await original<typeof import("../lib/upload")>()),
  uploadPhotos: vi.fn(),
}));

const photo = (id: string, over: Partial<AdminPhoto> = {}): AdminPhoto => ({
  id,
  title: "",
  place: null,
  aspectRatio: 1.5,
  exif: {},
  takenAt: null,
  status: "draft",
  allowDownload: false,
  sortPosition: 0,
  chapterId: null,
  unsplashId: null,
  variants: { "800": `http://cdn.test/${id}-800.webp`, "2400": `http://cdn.test/${id}-2400.webp` },
  createdAt: "2026-01-01T00:00:00Z",
  ...over,
});

const collection: AdminCollection = {
  id: "col1",
  slug: "goa",
  title: "Goa",
  place: "",
  year: "",
  intro: "",
  status: "published",
  sortPosition: 0,
  coverPhotoIds: [],
  chapters: [{ id: "ch1", collectionId: "col1", title: "Arrival", note: "", position: 0, photoIds: [] }],
};

let photos: AdminPhoto[];

function backend(extra: ReturnType<typeof route>[] = []) {
  return fakeBackend(
    route("GET", "/auth/me", json({ username: "nitish" })),
    route("GET", "/photos", () => json(photos)),
    route("GET", "/collections", json([collection])),
    ...extra,
  );
}

beforeEach(() => {
  photos = [
    photo("p1", { title: "Ghat at dusk", status: "published" }),
    photo("p2", { title: "", status: "draft" }),
    photo("p3", { title: "Temple", status: "published", allowDownload: true }),
  ];
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("photos page", () => {
  it("lists photos with a count, shows untitled ones plainly, and marks drafts", async () => {
    backend();
    renderAdmin();

    expect(await screen.findByText("3 photos · 2 published · 1 draft")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit Ghat at dusk" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit Untitled" })).toBeInTheDocument();
    expect(screen.getAllByText("Draft")).toHaveLength(1); // only the draft tile carries the badge
  });

  it("shows the 800px variant as the thumbnail", async () => {
    backend();
    renderAdmin();
    const tile = await screen.findByRole("button", { name: "Edit Ghat at dusk" });
    expect(within(tile).getByRole("img")).toHaveAttribute("src", "http://cdn.test/p1-800.webp");
  });

  it("filters to drafts or published", async () => {
    backend();
    renderAdmin();
    const user = userEvent.setup();
    await screen.findByText("3 photos · 2 published · 1 draft");

    await user.click(screen.getByRole("button", { name: /^Drafts/ }));
    expect(screen.queryByRole("button", { name: "Edit Ghat at dusk" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit Untitled" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^Published/ }));
    expect(screen.getByRole("button", { name: "Edit Ghat at dusk" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit Untitled" })).not.toBeInTheDocument();
  });

  it("invites you to upload when there are no photos yet", async () => {
    photos = [];
    backend();
    renderAdmin();
    expect(await screen.findByText(/no photos yet/i)).toBeInTheDocument();
  });

  it("opens an editor, saves a new title and place", async () => {
    const { calls } = backend([
      route("PATCH", "/photos/p2", (body) => json({ ...photo("p2"), ...(body as object) })),
    ]);
    renderAdmin();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Edit Untitled" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Title"), "Night market");
    await user.type(within(dialog).getByLabelText("Place"), "Indore");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ title: "Night market", place: "Indore" }),
    );
  });

  it("publishes and unpublishes from the editor", async () => {
    const { calls } = backend([
      route("POST", "/photos/p2/publish", json(photo("p2", { status: "published" }))),
      route("POST", "/photos/p1/unpublish", json(photo("p1"))),
    ]);
    renderAdmin();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Edit Untitled" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("switch", { name: "Published" }));
    await waitFor(() => expect(calls.some((c) => c.path === "/photos/p2/publish")).toBe(true));
  });

  it("turns downloads on and off per photo", async () => {
    const { calls } = backend([
      route("PUT", "/photos/p1/allow-download", (body) => json(photo("p1", { allowDownload: (body as { allow: boolean }).allow }))),
    ]);
    renderAdmin();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Edit Ghat at dusk" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("switch", { name: /allow downloads/i }));

    await waitFor(() =>
      expect(calls.find((c) => c.path === "/photos/p1/allow-download")?.body).toEqual({ allow: true }),
    );
  });

  it("asks before deleting, and does nothing if you cancel", async () => {
    const { calls } = backend([route("DELETE", "/photos/p2", noContent())]);
    renderAdmin();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Edit Untitled" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Delete photo" }));

    await user.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);

    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete photo" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path === "/photos/p2")).toBe(true));
  });

  it("puts a photo into a collection's chapter, or takes it out", async () => {
    const { calls } = backend([
      route("POST", "/chapters/ch1/photos", json({ id: "ch1" })),
      route("DELETE", "/chapters/ch1/photos/p1", noContent()),
    ]);
    renderAdmin();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Edit Ghat at dusk" }));
    const select = within(await screen.findByRole("dialog")).getByLabelText("Collection chapter");

    await user.selectOptions(select, "ch1");
    await waitFor(() => expect(calls.find((c) => c.path === "/chapters/ch1/photos")?.body).toEqual({ photoIds: ["p1"] }));
  });

  it("shows which chapter a photo is in and lets you remove it", async () => {
    photos = [photo("p1", { title: "Ghat", chapterId: "ch1", status: "published" })];
    const { calls } = backend([route("DELETE", "/chapters/ch1/photos/p1", noContent())]);
    renderAdmin();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Edit Ghat" }));
    const select = within(await screen.findByRole("dialog")).getByLabelText("Collection chapter");
    expect(select).toHaveValue("ch1");

    await user.selectOptions(select, "");
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path === "/chapters/ch1/photos/p1")).toBe(true));
  });

  it("publishes several selected photos at once", async () => {
    const { calls } = backend([
      route("POST", "/photos/p2/publish", json(photo("p2", { status: "published" }))),
    ]);
    renderAdmin();
    const user = userEvent.setup();
    await screen.findByText(/3 photos/);

    await user.click(screen.getByRole("checkbox", { name: "Select Untitled" }));
    expect(screen.getByText("1 selected")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Publish selected" }));

    await waitFor(() => expect(calls.filter((c) => c.path.endsWith("/publish")).map((c) => c.path)).toEqual(["/photos/p2/publish"]));
  });

  it("reorders by dragging one photo onto another", async () => {
    const { calls } = backend([route("PUT", "/photos/order", noContent())]);
    renderAdmin();
    await screen.findByText(/3 photos/);

    const tiles = screen.getAllByRole("listitem");
    fireEvent.dragStart(tiles[0]); // p1
    fireEvent.dragOver(tiles[2]);
    fireEvent.drop(tiles[2]); // onto p3

    await waitFor(() => expect(calls.find((c) => c.path === "/photos/order")?.body).toEqual({ ids: ["p2", "p3", "p1"] }));
  });

  it("moves a photo later with a button, for keyboard users", async () => {
    const { calls } = backend([route("PUT", "/photos/order", noContent())]);
    renderAdmin();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Edit Ghat at dusk" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Move later" }));
    await waitFor(() => expect(calls.find((c) => c.path === "/photos/order")?.body).toEqual({ ids: ["p2", "p1", "p3"] }));
  });

  it("uploads chosen files, then reports what worked and what did not", async () => {
    vi.mocked(upload.uploadPhotos).mockResolvedValue([
      { name: "a.jpg", ok: true, photoId: "x" },
      { name: "b.png", ok: false, error: "Only JPEG photos can be uploaded." },
    ]);
    backend();
    renderAdmin();
    // Dropped files (or "All files" in the picker) are not filtered by the input's accept list.
    const user = userEvent.setup({ applyAccept: false });
    await screen.findByText(/3 photos/);

    const files = [new File(["1"], "a.jpg", { type: "image/jpeg" }), new File(["2"], "b.png", { type: "image/png" })];
    await user.upload(screen.getByLabelText("Choose photo files"), files);

    expect(await screen.findByText(/1 uploaded/i)).toBeInTheDocument();
    expect(screen.getByText(/b\.png/)).toBeInTheDocument();
    expect(screen.getByText(/Only JPEG photos can be uploaded/)).toBeInTheDocument();
    expect(vi.mocked(upload.uploadPhotos).mock.calls[0][1]).toHaveLength(2);
  });
});
