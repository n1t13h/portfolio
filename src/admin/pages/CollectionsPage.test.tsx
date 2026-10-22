import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AdminCollection, AdminPhoto } from "../api/types";
import { fakeBackend, json, noContent, renderAdmin, route } from "../test/harness";

const photo = (id: string, title: string, over: Partial<AdminPhoto> = {}): AdminPhoto => ({
  id,
  title,
  place: null,
  aspectRatio: 1.5,
  exif: {},
  takenAt: null,
  status: "published",
  allowDownload: false,
  sortPosition: 0,
  chapterId: null,
  unsplashId: null,
  variants: { "800": `http://cdn.test/${id}.webp` },
  createdAt: "2026-01-01T00:00:00Z",
  ...over,
});

let collections: AdminCollection[];
let photos: AdminPhoto[];

const goa = (): AdminCollection => ({
  id: "col1",
  slug: "goa",
  title: "Goa",
  place: "India",
  year: "2024",
  intro: "Monsoon",
  status: "published",
  sortPosition: 0,
  coverPhotoIds: ["p1"],
  chapters: [
    { id: "ch1", collectionId: "col1", title: "Arrival", note: "Rain", position: 0, photoIds: ["p1", "p2"] },
    { id: "ch2", collectionId: "col1", title: "Beaches", note: "", position: 1, photoIds: ["p3"] },
  ],
});
const mumbai = (): AdminCollection => ({
  id: "col2", slug: "mumbai", title: "Mumbai", place: "", year: "", intro: "", status: "draft",
  sortPosition: 1, coverPhotoIds: [], chapters: [],
});

function backend(extra: ReturnType<typeof route>[] = []) {
  return fakeBackend(
    route("GET", "/auth/me", json({ username: "nitish" })),
    route("GET", "/collections", () => json(collections)),
    route("GET", "/photos", () => json(photos)),
    ...extra,
  );
}
const open = () => renderAdmin("/a/test-prefix/collections");
const chapter = (name: string) => screen.findByRole("region", { name: `Chapter ${name}` });

beforeEach(() => {
  collections = [goa(), mumbai()];
  photos = [
    photo("p1", "Ghat", { chapterId: "ch1" }),
    photo("p2", "Market", { chapterId: "ch1" }),
    photo("p3", "Temple", { chapterId: "ch2" }),
    photo("p4", "Spare"),
  ];
});
afterEach(() => vi.unstubAllGlobals());

describe("collections page", () => {
  it("lists collections with their status and opens the first one", async () => {
    backend();
    open();
    expect(await screen.findByRole("heading", { name: "Goa" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Mumbai/ })).toHaveTextContent("Draft");
    expect(screen.getByRole("button", { name: /^Goa/ })).toHaveTextContent("Published");
    expect(screen.getByLabelText("Slug")).toHaveValue("goa");
  });

  it("switches to another collection", async () => {
    backend();
    open();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /^Mumbai/ }));
    expect(await screen.findByRole("heading", { name: "Mumbai" })).toBeInTheDocument();
    expect(screen.getByText(/no chapters yet/i)).toBeInTheDocument();
  });

  it("saves edited details", async () => {
    const { calls } = backend([route("PATCH", "/collections/col1", (b) => json({ ...goa(), ...(b as object) }))]);
    open();
    const user = userEvent.setup();
    const title = await screen.findByLabelText("Title");
    await user.clear(title);
    await user.type(title, "Goa 2024");
    await user.clear(screen.getByLabelText("Intro"));
    await user.type(screen.getByLabelText("Intro"), "Rain and shacks");
    await user.click(screen.getByRole("button", { name: "Save details" }));

    await waitFor(() =>
      expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ title: "Goa 2024", intro: "Rain and shacks" }),
    );
  });

  it("publishes and unpublishes", async () => {
    const { calls } = backend([route("POST", "/collections/col1/unpublish", json({ ...goa(), status: "draft" }))]);
    open();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("switch", { name: "Published" }));
    await waitFor(() => expect(calls.some((c) => c.path === "/collections/col1/unpublish")).toBe(true));
  });

  it("creates a collection, suggesting a slug from the title", async () => {
    const { calls } = backend([
      route("POST", "/collections", (b) => json({ ...mumbai(), id: "col3", ...(b as object) }, 201)),
    ]);
    open();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "New collection" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Title"), "Kerala Backwaters");
    expect(within(dialog).getByLabelText("Slug")).toHaveValue("kerala-backwaters");
    await user.click(within(dialog).getByRole("button", { name: "Create" }));

    await waitFor(() =>
      expect(calls.find((c) => c.method === "POST" && c.path === "/collections")?.body).toEqual({
        slug: "kerala-backwaters",
        title: "Kerala Backwaters",
      }),
    );
  });

  it("explains a slug clash inside the dialog", async () => {
    backend([route("POST", "/collections", json({ detail: "slug already in use" }, 409))]);
    open();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "New collection" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Title"), "Goa");
    await user.click(within(dialog).getByRole("button", { name: "Create" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("slug already in use");
  });

  it("deletes a collection after confirmation", async () => {
    const { calls } = backend([route("DELETE", "/collections/col1", noContent())]);
    open();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Delete collection" }));
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path === "/collections/col1")).toBe(true));
  });

  it("reorders collections with the move buttons", async () => {
    const { calls } = backend([route("PUT", "/collections/order", noContent())]);
    open();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Move Goa later" }));
    await waitFor(() => expect(calls.find((c) => c.path === "/collections/order")?.body).toEqual({ ids: ["col2", "col1"] }));
  });

  it("reorders collections by dragging", async () => {
    const { calls } = backend([route("PUT", "/collections/order", noContent())]);
    open();
    await screen.findByRole("heading", { name: "Goa" });
    const rows = within(screen.getByRole("list", { name: "Collections" })).getAllByRole("listitem");
    fireEvent.dragStart(rows[1]);
    fireEvent.dragOver(rows[0]);
    fireEvent.drop(rows[0]);
    await waitFor(() => expect(calls.find((c) => c.path === "/collections/order")?.body).toEqual({ ids: ["col2", "col1"] }));
  });

  it("shows chapters in order with their photos", async () => {
    backend();
    open();
    const arrival = await chapter("Arrival");
    expect(within(arrival).getByLabelText("Chapter title")).toHaveValue("Arrival");
    expect(within(arrival).getByLabelText("Chapter note")).toHaveValue("Rain");
    const photosList = within(arrival).getByRole("list", { name: "Photos in Arrival" });
    expect(within(photosList).getAllByRole("img").map((i) => i.getAttribute("alt"))).toEqual(["Ghat", "Market"]);
  });

  it("adds a chapter", async () => {
    const { calls } = backend([
      route("POST", "/collections/col1/chapters", json({ id: "ch3", collectionId: "col1", title: "", note: "", position: 2, photoIds: [] }, 201)),
    ]);
    open();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Add chapter" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === "/collections/col1/chapters")).toBe(true));
  });

  it("edits a chapter's title and note", async () => {
    const { calls } = backend([route("PATCH", "/chapters/ch1", json({}))]);
    open();
    const user = userEvent.setup();
    const arrival = await chapter("Arrival");
    await user.type(within(arrival).getByLabelText("Chapter note"), " and mud");
    await user.click(within(arrival).getByRole("button", { name: "Save chapter" }));
    await waitFor(() => expect(calls.find((c) => c.path === "/chapters/ch1")?.body).toEqual({ note: "Rain and mud" }));
  });

  it("moves chapters up and down", async () => {
    const { calls } = backend([route("PUT", "/collections/col1/chapters/order", noContent())]);
    open();
    const user = userEvent.setup();
    const arrival = await chapter("Arrival");
    await user.click(within(arrival).getByRole("button", { name: "Move chapter down" }));
    await waitFor(() =>
      expect(calls.find((c) => c.path === "/collections/col1/chapters/order")?.body).toEqual({ ids: ["ch2", "ch1"] }),
    );
  });

  it("deletes a chapter after confirmation; its photos stay in the library", async () => {
    const { calls } = backend([route("DELETE", "/chapters/ch2", noContent())]);
    open();
    const user = userEvent.setup();
    const beaches = await chapter("Beaches");
    await user.click(within(beaches).getByRole("button", { name: "Delete chapter" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path === "/chapters/ch2")).toBe(true));
  });

  it("adds photos to a chapter from the library, noting where they currently are", async () => {
    const { calls } = backend([route("POST", "/chapters/ch2/photos", json({}))]);
    open();
    const user = userEvent.setup();
    const beaches = await chapter("Beaches");
    await user.click(within(beaches).getByRole("button", { name: "Add photos" }));
    const dialog = await screen.findByRole("dialog");

    expect(within(dialog).queryByLabelText("Select Temple")).not.toBeInTheDocument(); // already here
    expect(within(dialog).getAllByText("In Goa › Arrival")).toHaveLength(2); // Ghat and Market would be moved
    await user.click(within(dialog).getByLabelText("Select Spare"));
    await user.click(within(dialog).getByLabelText("Select Ghat"));
    await user.click(within(dialog).getByRole("button", { name: "Add selected" }));

    await waitFor(() => expect(calls.find((c) => c.path === "/chapters/ch2/photos")?.body).toEqual({ photoIds: ["p1", "p4"] }));
  });

  it("removes a photo from a chapter", async () => {
    const { calls } = backend([route("DELETE", "/chapters/ch1/photos/p2", noContent())]);
    open();
    const user = userEvent.setup();
    const arrival = await chapter("Arrival");
    await user.click(within(arrival).getByRole("button", { name: "Remove Market from chapter" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.path === "/chapters/ch1/photos/p2")).toBe(true));
  });

  it("reorders photos inside a chapter by dragging", async () => {
    const { calls } = backend([route("PUT", "/chapters/ch1/photos/order", noContent())]);
    open();
    const arrival = await chapter("Arrival");
    const items = within(within(arrival).getByRole("list", { name: "Photos in Arrival" })).getAllByRole("listitem");
    fireEvent.dragStart(items[0]);
    fireEvent.dragOver(items[1]);
    fireEvent.drop(items[1]);
    await waitFor(() => expect(calls.find((c) => c.path === "/chapters/ch1/photos/order")?.body).toEqual({ ids: ["p2", "p1"] }));
  });

  it("marks covers: the current one is pressed, others can be added or removed", async () => {
    const { calls } = backend([route("PUT", "/collections/col1/covers", json(goa()))]);
    open();
    const user = userEvent.setup();
    const arrival = await chapter("Arrival");
    expect(within(arrival).getByRole("button", { name: "Use Ghat as cover" })).toHaveAttribute("aria-pressed", "true");

    await user.click(within(arrival).getByRole("button", { name: "Use Market as cover" }));
    await waitFor(() => expect(calls.find((c) => c.path === "/collections/col1/covers")?.body).toEqual({ photoIds: ["p1", "p2"] }));
  });

  it("explains when the library has no photos to add", async () => {
    photos = [];
    collections = [{ ...goa(), chapters: [{ ...goa().chapters[0], photoIds: [] }] }];
    backend();
    open();
    const user = userEvent.setup();
    const arrival = await chapter("Arrival");
    await user.click(within(arrival).getByRole("button", { name: "Add photos" }));
    expect(await screen.findByText(/no other photos/i)).toBeInTheDocument();
  });
});
