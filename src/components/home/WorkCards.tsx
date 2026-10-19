import { site } from "@/content/site";
import { WorkVisual } from "./work-visuals";

export function WorkCards() {
  return (
    <section id="work" className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
      {site.projects.map((p) => (
        <article key={p.id} className="group">
          <div className="relative grid aspect-[4/3] sm:aspect-[16/10] place-items-center overflow-hidden rounded-[10px] bg-card">
            <div className="contents [&>*]:transition-transform [&>*]:duration-[900ms] [&>*]:ease-out group-hover:[&>*]:scale-[1.04] motion-reduce:[&>*]:transition-none motion-reduce:group-hover:[&>*]:scale-100">
              <WorkVisual kind={p.visual} />
            </div>
          </div>
          <h3 className="mt-3.5 text-base font-medium">{p.title}</h3>
          <div className="mt-[3px] text-sm text-mid">
            {p.description} · {p.stack.join(", ")}
          </div>
        </article>
      ))}
    </section>
  );
}
