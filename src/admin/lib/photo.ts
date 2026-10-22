import type { AdminPhoto } from "../api/types";

/** What to call a photo in the UI: its title, or "Untitled" while it has none. */
export const photoName = (photo: Pick<AdminPhoto, "title">) => photo.title.trim() || "Untitled";
