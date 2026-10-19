const COUNTRY_OR_STATE = new Set(["india"]);

const clean = (v) => (typeof v === "string" && v.trim() ? v.trim() : undefined);
const num = (v) => {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return typeof n === "number" && Number.isFinite(n) ? n : undefined;
};

function toPlace(location) {
  const parts = (location?.name ?? "").split(",").map((x) => x.trim()).filter(Boolean);
  // Just "India" or "<State>, India": too coarse to show.
  if (parts.length > 0 && parts.length <= 2 && parts[parts.length - 1].toLowerCase() === "india") {
    const c = clean(location?.city);
    return c && !COUNTRY_OR_STATE.has(c.toLowerCase()) ? c : undefined;
  }
  const first = clean(location?.name?.split(",")[0]);
  const city = clean(location?.city);
  const usable = first && !COUNTRY_OR_STATE.has(first.toLowerCase()) ? first : undefined;
  if (!usable) return city && !COUNTRY_OR_STATE.has(city.toLowerCase()) ? city : undefined;
  return city && city.toLowerCase() !== usable.toLowerCase() ? `${usable}, ${city}` : usable;
}

function toCamera(make, model) {
  const m = clean(make);
  const mod = clean(model);
  if (!mod) return m;
  if (m && !mod.toLowerCase().startsWith(m.toLowerCase())) return `${m} ${mod}`;
  return mod;
}

function toExif(exif) {
  if (!exif) return undefined;
  const out = {
    camera: toCamera(exif.make, exif.model),
    focalLength: num(exif.focal_length),
    aperture: num(exif.aperture),
    shutter: clean(exif.exposure_time),
    iso: num(exif.iso),
  };
  for (const k of Object.keys(out)) if (out[k] === undefined) delete out[k];
  return Object.keys(out).length ? out : undefined;
}

export function toSnapshotPhoto(api) {
  const title = clean(api.alt_description) ?? clean(api.description) ?? "Untitled";
  const photo = {
    id: api.id,
    pid: new URL(api.urls.raw).pathname.replace(/^\/photo-/, ""),
    aspectRatio: Math.round((api.width / api.height) * 1000) / 1000,
    title: title.charAt(0).toUpperCase() + title.slice(1),
  };
  const place = toPlace(api.location);
  if (place) photo.place = place;
  const exif = toExif(api.exif);
  if (exif) photo.exif = exif;
  photo.unsplashUrl = api.links.html;
  return photo;
}

// Ids not yet in the snapshot come first so rate-limited re-runs make progress.
export function orderForFetch(listedIds, existingIds) {
  const have = new Set(existingIds);
  return [...listedIds.filter((id) => !have.has(id)), ...listedIds.filter((id) => have.has(id))];
}
