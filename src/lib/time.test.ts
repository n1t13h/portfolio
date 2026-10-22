import { describe, it, expect } from "vitest";
import { formatIndiaTime } from "./time";

describe("formatIndiaTime", () => {
  it("formats Asia/Kolkata time", () =>
    expect(formatIndiaTime(new Date("2026-10-19T10:15:00Z"))).toBe("15:45, India"));
});
