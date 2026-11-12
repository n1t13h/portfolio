import { photoSrc, photoSrcSet } from "./images";
import type { Photo } from "@/data/photos";

const cdn = (w: number) => `https://cdn.ntshptl.in/photos/x/${w}.webp`;
const p: Photo = {
  id: "x",
  title: "t",
  aspectRatio: 1.5,
  variants: { "2400": cdn(2400), "800": cdn(800), "1600": cdn(1600) },
};

it("picks the smallest size at least as wide as asked", () => {
  expect(photoSrc(p, 500)).toBe(cdn(800));
  expect(photoSrc(p, 800)).toBe(cdn(800));
  expect(photoSrc(p, 1400)).toBe(cdn(1600));
});

it("falls back to the largest size when asked for more than exists", () => {
  expect(photoSrc(p, 3000)).toBe(cdn(2400));
  expect(photoSrc({ ...p, variants: { "800": cdn(800), "1600": cdn(1600) } }, 2000)).toBe(cdn(1600));
});

it("lists every size, smallest first, as a srcset", () => {
  expect(photoSrcSet(p)).toBe(`${cdn(800)} 800w, ${cdn(1600)} 1600w, ${cdn(2400)} 2400w`);
});

describe("portrait photos (size keys are the long edge, i.e. the height)", () => {
  const portrait: Photo = { ...p, aspectRatio: 0.667 };

  it("describes each size by its real width in the srcset", () => {
    expect(photoSrcSet(portrait)).toBe(`${cdn(800)} 534w, ${cdn(1600)} 1067w, ${cdn(2400)} 1601w`);
  });

  it("picks a size whose real width covers what was asked", () => {
    expect(photoSrc(portrait, 600)).toBe(cdn(1600)); // the 800 one is only 534 px wide
    expect(photoSrc(portrait, 500)).toBe(cdn(800));
  });
});
