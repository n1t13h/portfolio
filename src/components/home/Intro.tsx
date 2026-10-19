import { useCallback, useEffect, useRef, useState } from "react";
import { getPhotos, type Photo } from "@/data/photos";
import { imgUrl } from "@/lib/unsplash";

export const INTRO_KEY = "intro-played";
const DURATION = 3200;
const FADE = 700;
const CYCLE = 420;

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

// Positions/offsets follow the landing mockup (3 extra frames fill the 9-photo spread).
const FLOATS: {
  style: React.CSSProperties;
  dx: number;
  dy: number;
  delay: number;
  w: number;
}[] = [
  {
    style: { left: "3%", top: "-4%", width: "20%", height: "30%" },
    dx: -40,
    dy: -30,
    delay: 0.05,
    w: 600,
  },
  {
    style: { left: "44%", top: "-6%", width: "18%", height: "18%" },
    dx: 0,
    dy: -40,
    delay: 0.15,
    w: 500,
  },
  {
    style: { right: "-3%", top: "22%", width: "24%", height: "32%" },
    dx: 40,
    dy: 0,
    delay: 0.1,
    w: 500,
  },
  {
    style: { left: "-1%", top: "55%", width: "17%", height: "21%" },
    dx: -40,
    dy: 20,
    delay: 0.2,
    w: 600,
  },
  {
    style: { left: "24%", bottom: "-8%", width: "19%", height: "22%" },
    dx: 0,
    dy: 40,
    delay: 0.25,
    w: 500,
  },
  {
    style: { right: "20%", bottom: "-6%", width: "20%", height: "30%" },
    dx: 20,
    dy: 40,
    delay: 0.12,
    w: 600,
  },
  {
    style: { left: "22%", top: "8%", width: "12%", height: "16%" },
    dx: -30,
    dy: -20,
    delay: 0.18,
    w: 400,
  },
  {
    style: { right: "8%", top: "-3%", width: "14%", height: "17%" },
    dx: 30,
    dy: -30,
    delay: 0.08,
    w: 400,
  },
  {
    style: { right: "6%", bottom: "6%", width: "13%", height: "16%" },
    dx: 30,
    dy: 30,
    delay: 0.22,
    w: 400,
  },
];
const FLOAT_COUNT = FLOATS.length;
const WIN_COUNT = 5;

export function Intro({ onDone }: { onDone: () => void }) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [done, setDone] = useState(false);
  const [gone, setGone] = useState(false);
  const [active, setActive] = useState(0);
  const finished = useRef(false);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  const finish = useCallback(() => {
    if (finished.current) return;
    finished.current = true;
    try {
      window.sessionStorage.setItem(INTRO_KEY, "1");
    } catch {
      /* storage unavailable */
    }
    document.body.style.overflow = "";
    setDone(true);
    onDoneRef.current();
  }, []);

  useEffect(() => {
    let alive = true;
    getPhotos()
      .then((p) => {
        if (!alive) return;
        setPhotos(p);
        p.slice(0, Math.max(FLOAT_COUNT, WIN_COUNT)).forEach((ph, i) => {
          const img = new Image();
          img.src = imgUrl(ph.pid, i < FLOAT_COUNT ? FLOATS[i].w : 500);
        });
        p.slice(0, WIN_COUNT).forEach((ph) => {
          const img = new Image();
          img.src = imgUrl(ph.pid, 500);
        });
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    document.body.style.overflow = "hidden";
    const timer = setTimeout(finish, DURATION);
    const cycle = setInterval(
      () => setActive((a) => (a + 1) % WIN_COUNT),
      CYCLE,
    );
    const events = ["click", "wheel", "touchmove", "keydown"] as const;
    events.forEach((e) =>
      window.addEventListener(e, finish, { passive: true }),
    );
    return () => {
      clearTimeout(timer);
      clearInterval(cycle);
      events.forEach((e) => window.removeEventListener(e, finish));
      document.body.style.overflow = "";
    };
  }, [finish]);

  useEffect(() => {
    if (!done) return;
    const t = setTimeout(() => setGone(true), FADE);
    return () => clearTimeout(t);
  }, [done]);

  if (gone) return null;

  return (
    <div
      data-testid="intro"
      aria-hidden="true"
      className="fixed inset-0 z-50 overflow-hidden bg-white transition-[opacity,visibility] duration-700 ease-out"
      style={
        done
          ? { opacity: 0, visibility: "hidden", pointerEvents: "none" }
          : undefined
      }
    >
      <style>{`
        @keyframes intro-drift { 0% { opacity:0; transform:translate(var(--dx),var(--dy)) scale(.92); } 25% { opacity:1; } 100% { opacity:1; transform:none; } }
        @keyframes intro-open { to { width:1.9em; } }
      `}</style>
      {FLOATS.map((f, i) => (
        <div
          key={i}
          className="absolute overflow-hidden rounded-[10px] bg-[#f1f1f0] opacity-0"
          style={{
            ...f.style,
            ["--dx" as string]: `${f.dx}px`,
            ["--dy" as string]: `${f.dy}px`,
            animation: `intro-drift ${DURATION}ms cubic-bezier(.16,1,.3,1) ${f.delay}s forwards`,
          }}
        >
          {photos[i] && (
            <img
              src={imgUrl(photos[i].pid, f.w)}
              alt=""
              className="block h-full w-full object-cover"
            />
          )}
        </div>
      ))}
      <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center whitespace-nowrap text-[clamp(72px,9vw,150px)] font-medium tracking-[-.05em]">
        <span>nitish</span>
        <span
          className="relative mx-[.02em] h-[1.15em] w-0 overflow-hidden rounded-[12px]"
          style={{
            animation: "intro-open 1s cubic-bezier(.16,1,.3,1) .5s forwards",
          }}
        >
          {photos.slice(0, WIN_COUNT).map((p, i) => (
            <img
              key={p.id}
              src={imgUrl(p.pid, 500)}
              alt=""
              className="absolute inset-0 h-full w-full object-cover"
              style={{ opacity: i === active ? 1 : 0 }}
            />
          ))}
        </span>
        <span>patel</span>
      </div>
    </div>
  );
}
