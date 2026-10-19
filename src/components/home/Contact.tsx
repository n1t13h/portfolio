import { site } from "@/content/site";

declare global {
  interface Window {
    Calendly?: { initPopupWidget: (opts: { url: string }) => void };
  }
}

function bookCall() {
  if (window.Calendly) {
    window.Calendly.initPopupWidget({ url: site.links.calendly });
  } else {
    window.location.href = `mailto:${site.links.email}`;
  }
}

const socials = [
  { icon: "⌥", label: "GitHub", href: site.links.github },
  { icon: "in", label: "LinkedIn", href: site.links.linkedin },
  { icon: "◎", label: "Instagram", href: site.links.instagram },
  { icon: "@", label: "Email", href: `mailto:${site.links.email}` },
];

export function Contact() {
  const { heading, line, cta } = site.contact;
  return (
    <section id="contact" className="grid grid-cols-1 gap-7 md:grid-cols-[1fr_2fr]">
      <div>
        <h3 className="text-[22px] font-medium leading-[1.2] tracking-[-0.03em]">{heading}</h3>
        <p className="mb-[18px] mt-2.5 max-w-[300px] text-[15px] text-mid">{line}</p>
        <button type="button" onClick={bookCall} className="text-[22px] tracking-[-0.02em] hover:underline">
          {cta}
        </button>
      </div>
      <div className="grid grid-cols-2 gap-5 text-[15px] sm:grid-cols-4">
        {socials.map((s) => (
          <a
            key={s.label}
            href={s.href}
            {...(s.href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {})}
            className="flex flex-col gap-2"
          >
            <span aria-hidden="true" className="text-xl">
              {s.icon}
            </span>
            {s.label}
          </a>
        ))}
      </div>
    </section>
  );
}
