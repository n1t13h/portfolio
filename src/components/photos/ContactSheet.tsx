import { imgUrl } from "@/lib/unsplash";
import type { Photo } from "@/data/photos";

export function ContactSheet({ photos, onOpen }: { photos: Photo[]; onOpen: (id: string) => void }) {
  return (
    <div className="grid grid-cols-3 gap-[6px] sm:grid-cols-4 md:grid-cols-8">
      {photos.map((p) => (
        <button
          key={p.id}
          type="button"
          data-testid="sheet-photo"
          aria-label={p.title}
          onClick={() => onOpen(p.id)}
          className="group aspect-square cursor-zoom-in overflow-hidden rounded-[3px] bg-[#f1f1f0]"
        >
          <img
            src={imgUrl(p.pid, 400)}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover grayscale transition-[filter] duration-[400ms] motion-reduce:transition-none group-hover:grayscale-0"
          />
        </button>
      ))}
    </div>
  );
}
