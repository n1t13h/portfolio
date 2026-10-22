import { DEV_FLOAT_TILES, DEV_WINDOW_TILES } from "./devTileSets";
import { IntroStage } from "./IntroStage";
import { markIntroPlayed } from "./session";

/** The default site intro: "nitish ▢ patel" with developer tiles. */
export function DeveloperIntro() {
  return (
    <IntroStage
      testId="intro-developer"
      floatItems={DEV_FLOAT_TILES}
      windowItems={DEV_WINDOW_TILES}
      before="nitish"
      after="patel"
      duration={3200}
      wordmarkClass="whitespace-nowrap text-[clamp(38px,11vw,64px)] md:text-[clamp(72px,9vw,150px)]"
      onFinish={markIntroPlayed}
    />
  );
}
