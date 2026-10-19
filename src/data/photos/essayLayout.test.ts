import { describe, expect, it } from "vitest";
import { buildEssayBlocks, type EssayBlock } from "./essayLayout";
import type { Photo } from "./types";

const base: Photo = { id: "", pid: "pid", aspectRatio: 1, title: "t", unsplashUrl: "https://unsplash.com/photos/x" };
const L = (id: string): Photo => ({ ...base, id, aspectRatio: 1.5 });
const P = (id: string): Photo => ({ ...base, id, aspectRatio: 0.667 });
const kinds = (blocks: EssayBlock[]) => blocks.map((b) => b.kind);
const idsOf = (blocks: EssayBlock[]) =>
  blocks.flatMap((b) => (b.kind === "pair" ? b.photos.map((p) => p.id) : [b.photo.id]));

describe("buildEssayBlocks", () => {
  it("lands landscapes full width", () =>
    expect(kinds(buildEssayBlocks([L("a"), L("b")]))).toEqual(["full", "full"]));
  it("pairs two portraits", () =>
    expect(kinds(buildEssayBlocks([P("a"), P("b")]))).toEqual(["pair"]));
  it("never pairs twice in a row", () => {
    // Brief listed 4 portraits for [pair, offset, pair], which needs 5 photos.
    expect(kinds(buildEssayBlocks([P("a"), P("b"), P("c"), P("d"), P("e")]))).toEqual(["pair", "offset", "pair"]);
    expect(kinds(buildEssayBlocks([P("a"), P("b"), P("c"), P("d")]))).toEqual(["pair", "offset", "offset"]);
  });
  it("alternates offset sides", () => {
    const b = buildEssayBlocks([P("a"), L("x"), P("b"), L("y"), P("c")]);
    expect(b.flatMap((x) => (x.kind === "offset" ? [x.side] : []))).toEqual(["right", "left", "right"]);
  });
  it("puts the first offset after a pair on the right", () => {
    const b = buildEssayBlocks([P("a"), L("x"), P("b"), P("c"), P("d")]);
    expect(kinds(b)).toEqual(["offset", "full", "pair", "offset"]);
    expect(b.flatMap((x) => (x.kind === "offset" ? [x.side] : []))).toEqual(["right", "right"]);
  });
  it("keeps every photo exactly once, in order", () => {
    const input = [L("1"), P("2"), P("3"), P("4"), L("5"), P("6"), P("7"), P("8"), P("9")];
    expect(idsOf(buildEssayBlocks(input))).toEqual(input.map((p) => p.id));
  });
  it("returns [] for no photos", () => expect(buildEssayBlocks([])).toEqual([]));
});
