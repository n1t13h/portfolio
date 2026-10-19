import { useEffect, useRef, useState, type ReactNode } from "react";
import { formatPhotoMeta, type Photo } from "@/data/photos";
import type { EssayBlock as Block } from "@/data/photos/essayLayout";
import { imgUrl, srcSet } from "@/lib/unsplash";

const prefersReducedMotion = () =>
  typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function Reveal({ children, className }: { children: ReactNode; className: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(prefersReducedMotion);

  useEffect(() => {
    const el = ref.current;
    if (shown || !el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => entries.some((e) => e.isIntersecting) && setShown(true),
      { threshold: 0.12 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [shown]);

  return (
    <div
      ref={ref}
      className={`mb-14 transition-[opacity,transform] duration-[1200ms] ease-out motion-reduce:translate-y-0 motion-reduce:opacity-100 motion-reduce:transition-none ${
        shown ? "translate-y-0 opacity-100" : "translate-y-10 opacity-0"
      } ${className}`}
    >
      {children}
    </div>
  );
}

function Fig({ photo, width, sizes, className = "", onOpen }: {
  photo: Photo; width: number; sizes: string; className?: string; onOpen: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onOpen(photo.id)}
      aria-label={`Open ${photo.title}`}
      className={`block w-full cursor-zoom-in ${className}`}
    >
      <img
        loading="lazy"
        src={imgUrl(photo.pid, width)}
        srcSet={srcSet(photo.pid, [width / 2, width])}
        sizes={sizes}
        alt={photo.title}
        style={{ aspectRatio: photo.aspectRatio }}
        className="block w-full rounded-lg bg-[#f1f1f0] object-cover"
      />
    </button>
  );
}

const Mono = ({ photo, className = "" }: { photo: Photo; className?: string }) => (
  <span className={`font-mono text-xs text-[#9a9a9a] ${className}`}>{formatPhotoMeta(photo)}</span>
);

const Caption = ({ photo }: { photo: Photo }) => (
  <div className="mt-3 flex flex-col justify-between gap-1 text-sm sm:flex-row sm:gap-5">
    <span>{photo.title}</span>
    <Mono photo={photo} className="sm:text-right" />
  </div>
);

export function EssayBlock({ block, onOpen }: { block: Block; onOpen: (id: string) => void }) {
  if (block.kind === "full") {
    const p = block.photo;
    return (
      <Reveal className="">
        <Fig photo={p} width={2000} sizes="100vw" onOpen={onOpen} className="[&_img]:max-h-[86vh]" />
        <Caption photo={p} />
      </Reveal>
    );
  }
  if (block.kind === "pair") {
    return (
      <Reveal className="grid grid-cols-1 gap-[14px] md:grid-cols-2">
        {block.photos.map((p) => (
          <div key={p.id}>
            <Fig photo={p} width={1100} sizes="(min-width: 768px) 50vw, 100vw" onOpen={onOpen} />
            <Caption photo={p} />
          </div>
        ))}
      </Reveal>
    );
  }
  const p = block.photo;
  const right = block.side === "right";
  return (
    <Reveal className="grid grid-cols-1 items-end gap-[14px] md:grid-cols-12">
      <div className={right ? "md:col-span-5 md:col-start-6" : "md:col-span-5 md:col-start-2"}>
        <Fig photo={p} width={1200} sizes="(min-width: 768px) 42vw, 100vw" onOpen={onOpen} />
      </div>
      <div
        className={`order-last pb-0 md:order-none md:col-span-3 md:pb-10 md:row-start-1 ${
          right ? "md:col-start-2" : "md:col-start-8"
        }`}
      >
        <div className="text-[22px] leading-[1.3] tracking-[-0.03em]">{p.title}</div>
        <Mono photo={p} className="mt-3 block" />
      </div>
    </Reveal>
  );
}
