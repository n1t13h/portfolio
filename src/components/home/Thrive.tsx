import { useEffect, useRef, useState } from "react";
import { site } from "@/content/site";

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function BlurWords({ text }: { text: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const words = text.split(" ");
  const [reduced] = useState(prefersReducedMotion);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (reduced) return;
    const update = () => {
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight;
      setProgress(Math.min(1, Math.max(0, (vh * 0.9 - r.top) / (r.height + vh * 0.35))));
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [reduced]);

  return (
    <p
      ref={ref}
      className="text-[clamp(30px,2.9vw,46px)] font-normal leading-[1.14] tracking-[-0.035em]"
    >
      {words.map((w, i) => {
        const on = reduced || i / words.length < progress;
        return (
          <span key={i}>
            <span
              data-testid="blur-word"
              data-in={on ? "true" : "false"}
              className="transition-[opacity,filter] duration-[600ms] ease-out data-[in=false]:opacity-[.12] data-[in=false]:blur-[6px]"
            >
              {w}
            </span>
            {i < words.length - 1 ? " " : null}
          </span>
        );
      })}
    </p>
  );
}

export function Thrive() {
  const { kicker, paragraph, capabilities } = site.thrive;
  return (
    <section id="about" className="grid grid-cols-1 gap-7 md:grid-cols-[1fr_2fr]">
      <div className="text-[17px] text-[#333]">⁎ {kicker}</div>
      <div>
        <BlurWords text={paragraph} />
        <div className="mt-[38px] grid gap-[22px]">
          {capabilities.map((c) => (
            <div key={c.title}>
              <h4 className="text-xl font-medium tracking-[-0.02em]">{c.title}</h4>
              <p className="mt-1 text-[15px] text-mid">{c.line}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
