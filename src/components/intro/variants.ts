export const INTRO_PARAM = "intro";
export type IntroVariant = "developer" | "photos";

/** `?intro=developer` or `?intro=photos` (case-insensitive); anything else means "no variant". */
export function parseIntroVariant(search: string): IntroVariant | null {
  const value = new URLSearchParams(search).get(INTRO_PARAM)?.trim().toLowerCase();
  return value === "developer" || value === "photos" ? value : null;
}
