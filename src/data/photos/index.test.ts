import { collectionOf, findPhoto, getCollection, getCollections, getPhotos, photoKey } from "./index";

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

it("findPhoto matches a photo by its id or by its Unsplash id (old shared links)", async () => {
  const photos = await getPhotos();
  expect(findPhoto(photos, photos[0].id)).toBe(0);
  const fire = findPhoto(photos, "I5lzt9e4WMY");
  expect(fire).toBeGreaterThanOrEqual(0);
  expect(photos[fire].title).toBe("Performer creating a fiery hoop with fire");
  expect(findPhoto(photos, "nope")).toBe(-1);
});

it("photoKey prefers the Unsplash id so links keep their current form", async () => {
  const photos = await getPhotos();
  expect(photoKey(photos[0])).toBe(photos[0].unsplashId);
  expect(photoKey({ ...photos[0], unsplashId: undefined })).toBe(photos[0].id);
});

it("every photo has CDN image sizes", async () => {
  (await getPhotos()).forEach((p) => {
    expect(Object.keys(p.variants).length).toBeGreaterThan(0);
    Object.values(p.variants).forEach((url) => expect(url).toMatch(/^https:\/\/cdn\.ntshptl\.in\//));
  });
});
