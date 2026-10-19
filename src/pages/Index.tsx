import { useState } from "react";
import { Intro, shouldPlayIntro } from "@/components/home/Intro";
import { SiteNav } from "@/components/site/SiteNav";
import { SiteFooter } from "@/components/site/SiteFooter";
import { Hero } from "@/components/home/Hero";
import { WorkCards } from "@/components/home/WorkCards";
import { Thrive } from "@/components/home/Thrive";
import { ExperienceList } from "@/components/home/ExperienceList";
import { LensStrip } from "@/components/home/LensStrip";
import { Contact } from "@/components/home/Contact";

const Divider = () => <hr className="my-14 border-0 border-t border-line" />;

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Intro unmounts itself after its fade-out.
const noop = () => {};

const Index = () => {
  const [intro] = useState(() =>
    shouldPlayIntro(
      { getItem: (k) => window.sessionStorage.getItem(k) },
      prefersReducedMotion(),
    ),
  );
  return (
    <>
      {intro && <Intro onDone={noop} />}
      <SiteNav />
      <main
        data-testid="page-home"
        className="mx-auto max-w-[1520px] px-4 sm:px-7"
      >
        <Hero />
        <WorkCards />
        <Divider />
        <Thrive />
        <Divider />
        <ExperienceList />
        <Divider />
        <section id="lens">
          <LensStrip />
        </section>
        <Divider />
        <Contact />
      </main>
      <SiteFooter />
    </>
  );
};

export default Index;
