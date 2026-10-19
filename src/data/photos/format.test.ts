import { formatPhotoMeta } from "./format";

const base = { id: "a", pid: "1-x", aspectRatio: 1.5, title: "T", unsplashUrl: "u" };

it("formats full metadata", () => {
  expect(
    formatPhotoMeta({ ...base, place: "Ram Ghat, Ujjain", exif: { focalLength: 38, aperture: 36, shutter: "4", iso: 640 } }),
  ).toBe("Ram Ghat, Ujjain · 38mm · ƒ/36 · 4s · ISO 640");
});

it("omits missing parts without stray separators", () => {
  expect(formatPhotoMeta({ ...base, exif: { aperture: 5.6, shutter: "1/2500" } })).toBe("ƒ/5.6 · 1/2500s");
  expect(formatPhotoMeta({ ...base, place: "Mumbai" })).toBe("Mumbai");
  expect(formatPhotoMeta(base)).toBe("");
});
