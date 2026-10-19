import type { Photo } from "./types";

export type EssayBlock =
  | { kind: "full"; photo: Photo }
  | { kind: "pair"; photos: [Photo, Photo] }
  | { kind: "offset"; photo: Photo; side: "left" | "right" };

const isLandscape = (p: Photo) => p.aspectRatio > 1.1;

export function buildEssayBlocks(photos: Photo[]): EssayBlock[] {
  const blocks: EssayBlock[] = [];
  let side: "left" | "right" = "right";
  let k = 0;
  while (k < photos.length) {
    const a = photos[k];
    const b = photos[k + 1];
    const prevIsPair = blocks[blocks.length - 1]?.kind === "pair";
    if (isLandscape(a)) {
      blocks.push({ kind: "full", photo: a });
      k += 1;
    } else if (b && !isLandscape(b) && !prevIsPair) {
      blocks.push({ kind: "pair", photos: [a, b] });
      side = "right";
      k += 2;
    } else {
      blocks.push({ kind: "offset", photo: a, side });
      side = side === "right" ? "left" : "right";
      k += 1;
    }
  }
  return blocks;
}
