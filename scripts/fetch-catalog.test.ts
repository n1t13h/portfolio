import { describe, expect, it } from "vitest";
// @ts-expect-error plain .mjs script without types
import { buildCatalog, normalizePhoto } from "./fetch-catalog.mjs";

const variants = { "800": "https://cdn/x/800.webp" };
const apiPhoto = (over: Record<string, unknown> = {}) => ({
  id: "p1",
  title: "T",
  place: "Mumbai",
  aspectRatio: 1.5,
  exif: { camera: null, focalLength: null, aperture: null, shutter: null, iso: null },
  variants,
  allowDownload: false,
  downloadUrl: null,
  unsplashId: null,
  unsplashUrl: null,
  ...over,
});

describe("normalizePhoto", () => {
  it("drops an exif block that has nothing in it", () => {
    expect(normalizePhoto(apiPhoto())).not.toHaveProperty("exif");
  });

  it("keeps only the exif fields that have a value", () => {
    const p = normalizePhoto(apiPhoto({ exif: { camera: "Sony ZV-E10", iso: 640, aperture: null } }));
    expect(p.exif).toEqual({ camera: "Sony ZV-E10", iso: 640 });
  });

  it("leaves out empty download and Unsplash fields and the allowDownload flag", () => {
    const p = normalizePhoto(apiPhoto());
    for (const key of ["downloadUrl", "unsplashUrl", "unsplashId", "allowDownload"]) {
      expect(p).not.toHaveProperty(key);
    }
    expect(p).toMatchObject({ id: "p1", title: "T", place: "Mumbai", aspectRatio: 1.5, variants });
  });

  it("keeps download and Unsplash fields that are set", () => {
    const p = normalizePhoto(
      apiPhoto({ downloadUrl: "/photos/p1/download", unsplashId: "abc", unsplashUrl: "https://unsplash.com/photos/abc" }),
    );
    expect(p).toMatchObject({ downloadUrl: "/photos/p1/download", unsplashId: "abc", unsplashUrl: "https://unsplash.com/photos/abc" });
  });

  it("leaves out a missing place", () => {
    expect(normalizePhoto(apiPhoto({ place: null }))).not.toHaveProperty("place");
  });
});

const stub =
  (routes: Record<string, unknown>) =>
  async (path: string): Promise<unknown> => {
    const value = routes[path];
    if (value instanceof Error) throw value;
    if (value === undefined) throw new Error(`unexpected ${path}`);
    return value;
  };

describe("buildCatalog", () => {
  const detail = {
    slug: "a",
    title: "A",
    place: "",
    year: "2026",
    intro: "",
    covers: [apiPhoto()],
    chapters: [{ title: "t", note: "n", photos: [apiPhoto()] }],
    photos: [apiPhoto()],
  };

  it("collects every photo and each collection's full detail, normalised", async () => {
    const catalog = await buildCatalog(
      stub({ "/photos": [apiPhoto()], "/collections": [{ slug: "a" }], "/collections/a": detail }),
    );
    expect(catalog.photos).toHaveLength(1);
    expect(catalog.collections.map((c: { slug: string }) => c.slug)).toEqual(["a"]);
    const [c] = catalog.collections;
    expect(c.chapters[0].photos[0]).not.toHaveProperty("exif");
    expect(c.covers[0]).not.toHaveProperty("allowDownload");
    expect(c.photos[0]).not.toHaveProperty("downloadUrl");
  });

  it("refuses a catalog with no photos", async () => {
    await expect(buildCatalog(stub({ "/photos": [], "/collections": [] }))).rejects.toThrow(/no photos/i);
  });

  it("refuses a photo with no image sizes (the page could not show it)", async () => {
    await expect(
      buildCatalog(stub({ "/photos": [apiPhoto({ id: "bare", variants: {} })], "/collections": [] })),
    ).rejects.toThrow(/bare.*no image sizes/i);
  });

  it("fails when any collection can't be fetched", async () => {
    await expect(
      buildCatalog(stub({ "/photos": [apiPhoto()], "/collections": [{ slug: "a" }], "/collections/a": new Error("502") })),
    ).rejects.toThrow("502");
  });
});
