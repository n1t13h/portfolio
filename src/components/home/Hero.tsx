import { site } from "@/content/site";

export function Hero() {
  return (
    <section className="pb-[30px] pt-[38px]">
      <h1 className="text-[clamp(36px,3.4vw,54px)] font-medium leading-[1.05] tracking-[-0.045em]">
        {site.hero.headline}
      </h1>
      <p className="mt-4 text-[clamp(17px,1.35vw,21px)] text-mid">
        {site.hero.sub}{" "}
        <span
          aria-hidden="true"
          className="mb-0.5 ml-0.5 mr-1.5 inline-block h-2 w-2 rounded-full bg-ok shadow-[0_0_0_4px_rgba(31,191,95,.15)]"
        />
        <b className="font-medium text-ink">{site.hero.status}</b>
      </p>
    </section>
  );
}
