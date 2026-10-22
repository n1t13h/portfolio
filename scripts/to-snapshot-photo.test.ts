// @ts-expect-error plain .mjs script without types
import { orderForFetch, toSnapshotPhoto } from "./to-snapshot-photo.mjs";

const minimal = {
  id: "abcDEF-1234",
  width: 3000,
  height: 2000,
  alt_description: null,
  urls: { raw: "https://images.unsplash.com/photo-111-aaa?ixid=x" },
  links: { html: "https://unsplash.com/photos/abcDEF-1234" },
};

describe("toSnapshotPhoto", () => {
  it("maps an Unsplash API photo to a snapshot Photo", () => {
    const api = {
      id: "I5lzt9e4WMY",
      width: 2667,
      height: 4000,
      alt_description: "performer creating a fiery hoop with fire",
      urls: { raw: "https://images.unsplash.com/photo-1775585571531-1d0f9df8c144?ixid=abc" },
      links: { html: "https://unsplash.com/photos/I5lzt9e4WMY" },
      exif: { make: "Sony", model: "ZV-E10", focal_length: "38.0", aperture: "36.0", exposure_time: "4", iso: 640 },
      location: { name: "Ram Ghat, Kartik Chowk, Ujjain, Madhya Pradesh, India", city: "Ujjain" },
    };
    expect(toSnapshotPhoto(api)).toEqual({
      id: "I5lzt9e4WMY",
      pid: "1775585571531-1d0f9df8c144",
      aspectRatio: 0.667,
      title: "Performer creating a fiery hoop with fire",
      place: "Ram Ghat, Ujjain",
      exif: { camera: "Sony ZV-E10", focalLength: 38, aperture: 36, shutter: "4", iso: 640 },
      unsplashUrl: "https://unsplash.com/photos/I5lzt9e4WMY",
    });
  });

  it("omits exif and place when Unsplash has none", () => {
    const p = toSnapshotPhoto({
      ...minimal,
      exif: { make: null, model: null, focal_length: null, aperture: null, exposure_time: null, iso: null },
      location: { name: null },
    });
    expect(p.exif).toBeUndefined();
    expect(p.place).toBeUndefined();
    expect(p.title).toBe("Untitled");
  });

  it("keeps ids with dashes, avoids a doubled make, and drops India-only places", () => {
    const p = toSnapshotPhoto({
      ...minimal,
      exif: { make: "Canon", model: "Canon EOS R5", iso: 100 },
      location: { name: "India", city: null },
    });
    expect(p.id).toBe("abcDEF-1234");
    expect(p.exif).toEqual({ camera: "Canon EOS R5", iso: 100 });
    expect(p.place).toBeUndefined();
  });
});

describe("state-only places", () => {
  it("keeps the city for 'Mumbai, India'", () => {
    expect(toSnapshotPhoto({ ...minimal, location: { name: "Mumbai, India", city: "Mumbai" } }).place).toBe("Mumbai");
  });
  it("yields no place for 'Madhya Pradesh, India' without a city", () => {
    expect(toSnapshotPhoto({ ...minimal, location: { name: "Madhya Pradesh, India" } }).place).toBeUndefined();
  });
  it("drops '<State>, India'", () => {
    expect(toSnapshotPhoto({ ...minimal, location: { name: "Madhya Pradesh, India", city: null } }).place).toBeUndefined();
  });
});

describe("orderForFetch", () => {
  it("puts ids missing from the snapshot first", () => {
    expect(orderForFetch(["a", "b", "c", "d"], ["a", "c"])).toEqual(["b", "d", "a", "c"]);
  });
});
