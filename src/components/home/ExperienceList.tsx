import { site } from "@/content/site";

export function ExperienceList() {
  return (
    <section id="experience" className="grid grid-cols-1 gap-7 md:grid-cols-[1fr_2fr]">
      <div className="text-[17px] text-[#333]">⁎ Experience</div>
      <div>
        {site.experience.map((e, i, all) => (
          <div
            key={`${e.company}-${e.years}`}
            className={`grid grid-cols-[1fr_auto] gap-x-4 border-t border-line py-[18px] text-[19px] tracking-[-0.02em] sm:grid-cols-[1fr_1fr_auto] ${
              i === all.length - 1 ? "border-b" : ""
            }`}
          >
            <span>{e.company}</span>
            <span className="text-mid max-sm:col-start-1 max-sm:row-start-2">{e.role}</span>
            <span className="text-[15px] tabular-nums text-soft max-sm:row-span-2 max-sm:self-center">{e.years}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
