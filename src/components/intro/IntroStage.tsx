import { useCallback, useEffect, useRef, useState } from "react";
import type { Photo } from "@/data/photos";
import { imgUrl } from "@/lib/unsplash";
import { FLOATS } from "./floats";

const FADE = 700;
const CYCLE = 420;
// Skip listeners arm after this delay: the click/keypress that opened the page is still being
// dispatched when the stage mounts and would otherwise skip the intro it just started.
const SKIP_GRACE = 300;


type IntroStageProps = {
  testId: string;
  /** Photos for the floating tiles, index-aligned with FLOATS; missing ones render nothing. */
  floatPhotos: Photo[];
  /** Photos cycled inside the wordmark's window. */
  windowPhotos: Photo[];
  before: string;
  after?: string;
  duration: number;
  /** Size/wrapping classes for the wordmark. */
  wordmarkClass: string;
  /** Called once when the stage ends, by timer or by the visitor skipping it. */
  onFinish: () => void;
};

/**
 * Full-screen overlay: photos drift in around a wordmark whose window cycles through
 * more photos. Ends after `duration`, or on click / wheel / touch / key; fades out and
 * unmounts itself. Callers decide whether to show it at all (reduced motion, once-only).
 */
export function IntroStage({
  testId,
  floatPhotos,
  windowPhotos,
  before,
  after,
  duration,
  wordmarkClass,
  onFinish,
}: IntroStageProps) {
  const [done, setDone] = useState(false);
  const [gone, setGone] = useState(false);
  const [tick, setTick] = useState(0);
  const finished = useRef(false);
  const onFinishRef = useRef(onFinish);

  useEffect(() => {
    onFinishRef.current = onFinish;
  });

  const finish = useCallback(() => {
    if (finished.current) return;
    finished.current = true;
    document.body.style.overflow = "";
    setDone(true);
    onFinishRef.current();
  }, []);

  useEffect(() => {
    document.body.style.overflow = "hidden";
    const timer = setTimeout(finish, duration);
    const cycle = setInterval(() => setTick((t) => t + 1), CYCLE);
    const events = ["click", "wheel", "touchmove", "keydown"] as const;
    const arm = setTimeout(
      () => events.forEach((e) => window.addEventListener(e, finish, { passive: true })),
      SKIP_GRACE,
    );
    return () => {
      clearTimeout(timer);
      clearTimeout(arm);
      clearInterval(cycle);
      events.forEach((e) => window.removeEventListener(e, finish));
      document.body.style.overflow = "";
    };
  }, [finish, duration]);

  useEffect(() => {
    if (!done) return;
    const t = setTimeout(() => setGone(true), FADE);
    return () => clearTimeout(t);
  }, [done]);

  if (gone) return null;

  const active = windowPhotos.length ? tick % windowPhotos.length : 0;

  return (
    <div
      data-testid={testId}
      aria-hidden="true"
      className="fixed inset-0 z-50 overflow-hidden bg-white transition-[opacity,visibility] duration-700 ease-out"
      style={done ? { opacity: 0, visibility: "hidden", pointerEvents: "none" } : undefined}
    >
      <style>{`
        @keyframes intro-drift { 0% { opacity:0; transform:translate(var(--dx),var(--dy)) scale(.92); } 25% { opacity:1; } 100% { opacity:1; transform:none; } }
        @keyframes intro-open { to { width:1.9em; } }
      `}</style>
      {FLOATS.map((f, i) =>
        i < floatPhotos.length || floatPhotos.length === 0 ? (
          <div
            key={i}
            className="absolute overflow-hidden rounded-[10px] bg-[#f1f1f0] opacity-0"
            style={{
              ...f.style,
              ["--dx" as string]: `${f.dx}px`,
              ["--dy" as string]: `${f.dy}px`,
              animation: `intro-drift ${duration}ms cubic-bezier(.16,1,.3,1) ${f.delay}s forwards`,
            }}
          >
            {floatPhotos[i] && (
              <img src={imgUrl(floatPhotos[i].pid, f.w)} alt="" className="block h-full w-full object-cover" />
            )}
          </div>
        ) : null,
      )}
      <div
        className={`absolute left-1/2 top-1/2 z-10 flex -translate-x-1/2 -translate-y-1/2 items-center font-medium tracking-[-.05em] ${wordmarkClass}`}
      >
        <span>{before}</span>
        <span
          className="relative mx-[.02em] h-[1.15em] w-0 shrink-0 overflow-hidden rounded-[12px]"
          style={{ animation: "intro-open 1s cubic-bezier(.16,1,.3,1) .5s forwards" }}
        >
          {windowPhotos.map((p, i) => (
            <img
              key={p.id}
              src={imgUrl(p.pid, 500)}
              alt=""
              className="absolute inset-0 h-full w-full object-cover"
              style={{ opacity: i === active ? 1 : 0 }}
            />
          ))}
        </span>
        {after && <span>{after}</span>}
      </div>
    </div>
  );
}
