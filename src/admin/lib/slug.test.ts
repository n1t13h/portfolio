import { describe, expect, it } from "vitest";
import { slugify } from "./slug";

describe("slugify", () => {
  it("makes a URL-safe slug from a title", () => {
    expect(slugify("Kerala Backwaters")).toBe("kerala-backwaters");
  });

  it("drops accents, punctuation and repeated separators", () => {
    expect(slugify("  Café — Mumbai!!  2024 ")).toBe("cafe-mumbai-2024");
  });

  it("matches what the server accepts: lowercase words joined by single hyphens", () => {
    expect(slugify("Ujjain · Omkareshwar · Indore")).toBe("ujjain-omkareshwar-indore");
    expect(slugify("---")).toBe("");
  });
});
