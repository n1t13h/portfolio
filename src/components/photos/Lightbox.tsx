import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { collectionOf, formatPhotoMeta } from "@/data/photos";
import type { Photo, ResolvedCollection } from "@/data/photos";
import { imgUrl, srcSet } from "@/lib/unsplash";

const PARAM = "photo";

export function useLightboxParam() {
  const [params, setParams] = useSearchParams();
  const photoId = params.get(PARAM);
  const set = useCallback(
    (id: string | null) =>
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (id === null) next.delete(PARAM);
          else next.set(PARAM, id);
          return next;
        },
        { replace: true },
      ),
    [setParams],
  );
  return {
    photoId,
    open: useCallback((id: string) => set(id), [set]),
    close: useCallback(() => set(null), [set]),
  };
}

const pad = (n: number) => String(n).padStart(2, "0");
const FOCUSABLE = "a[href], button:not([disabled])";

export function Lightbox({
  photos,
  collections,
}: {
  photos: Photo[];
  collections: ResolvedCollection[];
}) {
  const { photoId, open, close } = useLightboxParam();
  const index = photoId === null ? -1 : photos.findIndex((p) => p.id === photoId);
  const isOpen = index >= 0;
  const root = useRef<HTMLDivElement>(null);
  const closeBtn = useRef<HTMLButtonElement>(null);
  // Id of the photo whose fade-in has started. Keyed to the photo so a newly
  // shown image starts hidden on its very first render, then fades in once.
  const [shownId, setShownId] = useState<string | null>(null);
  const shown = isOpen && shownId === photoId;

  const total = photos.length;
  const go = useCallback(
    (delta: number) => open(photos[(index + delta + total) % total].id),
    [open, photos, index, total],
  );

  // Scroll lock, initial focus and focus restore.
  useEffect(() => {
    if (!isOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";
    closeBtn.current?.focus();
    return () => {
      document.body.style.overflow = "";
      previous?.focus?.();
    };
  }, [isOpen]);

  // Keyboard: arrows, escape, focus trap.
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === "ArrowRight") go(1);
      else if (e.key === "Tab" && root.current) {
        const items = Array.from(root.current.querySelectorAll<HTMLElement>(FOCUSABLE));
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        const active = document.activeElement;
        if (e.shiftKey && (active === first || !root.current.contains(active))) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && (active === last || !root.current.contains(active))) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, close, go]);

  // Fade/scale the image in for each new photo.
  useEffect(() => {
    if (!isOpen) {
      setShownId(null); // so reopening the same photo fades in again
      return;
    }
    const raf = requestAnimationFrame(() => setShownId(photoId));
    return () => cancelAnimationFrame(raf);
  }, [photoId, isOpen]);

  if (!isOpen) return null;
  const photo = photos[index];
  const meta = formatPhotoMeta(photo);
  const collection = collectionOf(photo.id, collections);

  return (
    <div
      ref={root}
      role="dialog"
      aria-modal="true"
      aria-label="Photo viewer"
      className="fixed inset-0 z-[70] grid grid-rows-[64px_1fr_auto] bg-white/[.96] backdrop-blur-[20px]"
    >
      <div className="flex items-center justify-between px-4 sm:px-7">
        <span data-testid="lightbox-counter" className="font-mono text-[13px] text-[#6b6b6b]">
          {pad(index + 1)} / {pad(total)}
        </span>
        <button
          ref={closeBtn}
          type="button"
          onClick={close}
          className="text-[15px] text-[#6b6b6b] hover:text-[#0b0b0b]"
        >
          Close · esc
        </button>
      </div>
      <div
        data-testid="lightbox-backdrop"
        onClick={(e) => {
          if (e.target === e.currentTarget) close();
        }}
        className="relative grid min-h-0 place-items-center px-4 sm:px-[90px]"
      >
        <button
          type="button"
          aria-label="Previous photo"
          onClick={() => go(-1)}
          className="absolute left-2 top-1/2 z-10 h-10 w-10 -translate-y-1/2 rounded-full border border-line bg-white/90 text-lg sm:h-12 sm:w-12 sm:bg-white transition-transform duration-300 ease-out hover:scale-[1.04] motion-reduce:transition-none sm:left-6"
        >
          ←
        </button>
        <img
          key={photo.id}
          src={imgUrl(photo.pid, 1400)}
          srcSet={srcSet(photo.pid, [800, 1400, 2000])}
          sizes="(min-width: 640px) calc(100vw - 180px), 100vw"
          alt={photo.title}
          className={`max-h-[calc(100vh-160px)] max-w-full rounded-md shadow-[0_30px_80px_rgba(0,0,0,.12)] transition-[transform,opacity] duration-[600ms] ease-out motion-reduce:transition-none motion-reduce:opacity-100 motion-reduce:scale-100 ${
            shown ? "scale-100 opacity-100" : "scale-[.97] opacity-0"
          }`}
        />
        <button
          type="button"
          aria-label="Next photo"
          onClick={() => go(1)}
          className="absolute right-2 top-1/2 z-10 h-10 w-10 -translate-y-1/2 rounded-full border border-line bg-white/90 text-lg sm:h-12 sm:w-12 sm:bg-white transition-transform duration-300 ease-out hover:scale-[1.04] motion-reduce:transition-none sm:right-6"
        >
          →
        </button>
      </div>
      <div className="grid grid-cols-1 items-baseline gap-x-7 gap-y-2 px-4 pb-6 pt-[18px] sm:grid-cols-[1fr_auto_auto] sm:px-7">
        <div>
          <h3 className="text-base font-medium">{photo.title}</h3>
          {meta && <span className="mt-1 block font-mono text-[13px] text-[#6b6b6b]">{meta}</span>}
        </div>
        {collection && (
          <Link
            to={`/photos/${collection.slug}`}
            className="text-[15px] text-[#6b6b6b] hover:text-[#0b0b0b]"
          >
            From {collection.title} →
          </Link>
        )}
        <a
          href={photo.unsplashUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[15px] text-[#6b6b6b] hover:text-[#0b0b0b]"
        >
          Unsplash ↗
        </a>
      </div>
    </div>
  );
}
