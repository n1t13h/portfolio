export const INTRO_KEY = "intro-played";

export function shouldPlayIntro(
  storage: Pick<Storage, "getItem">,
  reducedMotion: boolean,
): boolean {
  if (reducedMotion) return false;
  try {
    return storage.getItem(INTRO_KEY) === null;
  } catch {
    return false;
  }
}

/** Remembers that an intro has played so the default intro doesn't replay later in this session. */
export function markIntroPlayed() {
  try {
    window.sessionStorage.setItem(INTRO_KEY, "1");
  } catch {
    /* storage unavailable */
  }
}
