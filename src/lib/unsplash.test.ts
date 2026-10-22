import { imgUrl, srcSet } from "./unsplash";

it("builds sized urls", () => {
  expect(imgUrl("1-x", 600)).toBe("https://images.unsplash.com/photo-1-x?w=600&q=80&auto=format");
  expect(srcSet("1-x", [400, 800])).toBe(
    "https://images.unsplash.com/photo-1-x?w=400&q=80&auto=format 400w, https://images.unsplash.com/photo-1-x?w=800&q=80&auto=format 800w",
  );
});
