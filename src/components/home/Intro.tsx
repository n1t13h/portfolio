import { useCallback, useEffect, useState } from "react";
import { getPhotos, type Photo } from "@/data/photos";
import { imgUrl } from "@/lib/unsplash";
import { IntroStage, PhotoImg } from "@/components/intro/IntroStage";
import { FLOATS, FLOAT_COUNT } from "@/components/intro/floats";
import { markIntroPlayed } from "@/components/intro/session";

const DURATION = 3200;
const WIN_COUNT = 5;

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
    markIntroPlayed();
    onDone();
  }, [onDone]);

  return (
    <IntroStage
      testId="intro"
      floatItems={photos.slice(0, FLOAT_COUNT).map((p, i) => (
        <PhotoImg key={p.id} photo={p} width={FLOATS[i].w} />
      ))}
      windowItems={photos.slice(0, WIN_COUNT).map((p) => (
        <PhotoImg key={p.id} photo={p} width={500} />
      ))}
      before="nitish"
      after="patel"
      duration={DURATION}
      wordmarkClass="whitespace-nowrap text-[clamp(38px,11vw,64px)] md:text-[clamp(72px,9vw,150px)]"
      onFinish={handleFinish}
    />
  );
}
