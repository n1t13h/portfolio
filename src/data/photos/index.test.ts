import snapshot from "./snapshot.json";
import curation from "./curation";
import { collectionOf, getCollection, getPhotos, getCollections, orderPhotos, resolveCollections } from "./index";
import type { Collection, Photo } from "./types";

const photo = (id: string): Photo => ({ id, pid: `p-${id}`, aspectRatio: 1.5, title: id, unsplashUrl: "u" });
const col = (partial: Partial<Collection>): Collection => ({
  slug: "s", title: "S", place: "P", year: "2026", intro: "", coverIds: [], chapters: [], ...partial,
});

it("drops curated ids missing from the snapshot and warns", () => {
  const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
  const [c] = resolveCollections([photo("a")], {
    order: [], excluded: [],
    collections: [col({ coverIds: ["a", "ghost"], chapters: [{ title: "x", note: "", photoIds: ["ghost", "a"] }] })],
  });
  expect(c.chapters[0].photos.map((p) => p.id)).toEqual(["a"]);
  expect(c.covers.map((p) => p.id)).toEqual(["a"]);
  expect(warn).toHaveBeenCalledWith(expect.stringContaining("ghost"));
  warn.mockRestore();
});

it("orderPhotos drops exclusions and follows order, then the rest", () => {
  expect(
    orderPhotos([photo("a"), photo("b"), photo("c")], { order: ["c"], excluded: ["b"], collections: [] }).map((p) => p.id),
  ).toEqual(["c", "a"]);
});

it("getCollection returns null for an unknown slug", async () => {
  expect(await getCollection("nope")).toBeNull();
});

it("real data: every collection has photos and the MP collection has 22", async () => {
  const cols = await getCollections();
  expect(cols.find((c) => c.slug === "ujjain-omkareshwar-indore")!.photos).toHaveLength(22);
  cols.forEach((c) => expect(c.photos.length).toBeGreaterThan(0));
});

it("collectionOf finds the owning collection", async () => {
  const cols = await getCollections();
  const id = cols[1].photos[0].id;
  expect(collectionOf(id, cols)?.slug).toBe(cols[1].slug);
  expect(collectionOf("ghost", cols)).toBeUndefined();
});

it("snapshot ids are the Unsplash id (last 11 chars of the url slug) and unique", () => {
  const ids = (snapshot as Photo[]).map((p) => p.id);
  (snapshot as Photo[]).forEach((p) => {
    const last = p.unsplashUrl.split("/").pop()!;
    expect(p.id).toHaveLength(11);
    expect(last.endsWith(p.id)).toBe(true);
  });
  expect(new Set(ids).size).toBe(ids.length);
});

it("getPhotos omits excluded ids and starts with order[0]", async () => {
  const photos = await getPhotos();
  curation.excluded.forEach((id) => expect(photos.map((p) => p.id)).not.toContain(id));
  expect(photos[0].id).toBe(curation.order[0]);
});
