import { useEffect, useRef, useState } from "react";
import { imgUrl } from "@/lib/unsplash";
import type { Photo } from "@/data/photos";

const ROTATIONS = [-4, 3, -1, 5];
const OFFSET = { x: 30, y: -160 };

function canFollowPointer() {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return (
    window.matchMedia("(hover: hover)").matches &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function CursorStack({ photos, active }: { photos: Photo[]; active: boolean }) {
  const [enabled] = useState(canFollowPointer);
  const ref = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    const target = { x: 0, y: 0 };
    const pos = { x: 0, y: 0 };
    let seeded = false;
    let raf = 0;
    const onMove = (e: PointerEvent) => {
      target.x = e.clientX + OFFSET.x;
      target.y = e.clientY + OFFSET.y;
      if (!seeded) {
        pos.x = target.x;
        pos.y = target.y;
        seeded = true;
      }
    };
    const tick = () => {
      pos.x += (target.x - pos.x) * 0.14;
      pos.y += (target.y - pos.y) * 0.14;
      if (ref.current) ref.current.style.transform = `translate3d(${pos.x}px, ${pos.y}px, 0)`;
      raf = requestAnimationFrame(tick);
    };
    window.addEventListener("pointermove", onMove);
    raf = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(raf);
    };
  }, [enabled]);

  useEffect(() => {
    setIndex(0);
    if (!enabled || !active || photos.length < 2) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % photos.length), 650);
    return () => window.clearInterval(id);
  }, [enabled, active, photos]);

  if (!enabled) return null;

  return (
    <div
      ref={ref}
      data-testid="cursor-stack"
      aria-hidden="true"
      className={`pointer-events-none fixed left-0 top-0 z-[15] h-[320px] w-[260px] transition-opacity duration-300 ${
        active ? "opacity-100" : "opacity-0"
      }`}
    >
      {photos.map((p, i) => (
        <img
          key={p.id}
          src={imgUrl(p.pid, 600)}
          alt=""
          style={{ transform: `scale(${i === index ? 1 : 0.94}) rotate(${ROTATIONS[i % ROTATIONS.length]}deg)` }}
          className={`absolute inset-0 h-full w-full rounded-[6px] object-cover shadow-[0_30px_60px_rgba(0,0,0,.18)] transition-[opacity,transform] duration-500 ease-out ${
            i === index ? "opacity-100" : "opacity-0"
          }`}
        />
      ))}
    </div>
  );
}
