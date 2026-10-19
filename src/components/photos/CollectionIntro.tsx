import type { ResolvedCollection } from "@/data/photos";
import { IntroStage, PhotoImg } from "@/components/intro/IntroStage";
import { FLOATS } from "@/components/intro/floats";
import { pickIntroPhotos, splitTitle } from "./introPhotos";

const DURATION = 2600;

/** Plays when a collection opens: the collection's name in the wordmark, its own photos around it. */
export function CollectionIntro({ collection }: { collection: ResolvedCollection }) {
  const { before, after } = splitTitle(collection.title);
  const { floatPhotos, windowPhotos } = pickIntroPhotos(collection);
  return (
    <IntroStage
      testId="collection-intro"
      floatItems={floatPhotos.map((p, i) => (
        <PhotoImg key={p.id} photo={p} width={FLOATS[i].w} />
      ))}
      windowItems={windowPhotos.map((p) => (
        <PhotoImg key={p.id} photo={p} width={500} />
      ))}
      before={before}
      after={after}
      duration={DURATION}
      wordmarkClass="w-[60vw] flex-wrap md:w-[70vw] justify-center text-center text-[clamp(34px,4.2vw,72px)]"
      onFinish={() => {}}
    />
  );
}
