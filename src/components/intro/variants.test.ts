import { describe, expect, it } from "vitest";
import { parseIntroVariant } from "./variants";

describe("parseIntroVariant", () => {
  it("reads developer and photos, ignoring case and spaces", () => {
    expect(parseIntroVariant("?intro=developer")).toBe("developer");
    expect(parseIntroVariant("?intro=photos")).toBe("photos");
    expect(parseIntroVariant("?x=1&intro=DEVELOPER")).toBe("developer");
    expect(parseIntroVariant("?intro=%20Photos%20")).toBe("photos");
  });
  it("returns null for a missing, empty or unknown value", () => {
    expect(parseIntroVariant("")).toBeNull();
    expect(parseIntroVariant("?intro=")).toBeNull();
    expect(parseIntroVariant("?intro=wedding")).toBeNull();
    expect(parseIntroVariant("?other=developer")).toBeNull();
  });
});
