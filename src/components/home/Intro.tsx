import { useCallback, useEffect, useState } from "react";
import { getPhotos, type Photo } from "@/data/photos";
import { imgUrl } from "@/lib/unsplash";
import { IntroStage } from "@/components/intro/IntroStage";
import { FLOATS, FLOAT_COUNT } from "@/components/intro/floats";

export const INTRO_KEY = "intro-played";
const DURATION = 3200;
const WIN_COUNT = 5;

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

export function Intro({ onDone }: { onDone: () => void }) {
  const [photos, setPhotos] = useState<Photo[]>([]);

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
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const handleFinish = useCallback(() => {
    try {
      window.sessionStorage.setItem(INTRO_KEY, "1");
    } catch {
      /* storage unavailable */
    }
    onDone();
  }, [onDone]);

  return (
    <IntroStage
      testId="intro"
      floatPhotos={photos.slice(0, FLOAT_COUNT)}
      windowPhotos={photos.slice(0, WIN_COUNT)}
      before="nitish"
      after="patel"
      duration={DURATION}
      wordmarkClass="whitespace-nowrap text-[clamp(72px,9vw,150px)]"
      onFinish={handleFinish}
    />
  );
}
