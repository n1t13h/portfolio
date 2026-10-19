import { useState } from "react";
import { DeveloperIntro } from "@/components/intro/DeveloperIntro";
import { shouldPlayIntro } from "@/components/intro/session";
import { parseIntroVariant } from "@/components/intro/variants";
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

const Index = () => {
  // An explicit ?intro= variant is played by <IntroGate />, so the default intro steps aside.
  const [intro] = useState(
    () =>
      parseIntroVariant(window.location.search) === null &&
      shouldPlayIntro(
        { getItem: (k) => window.sessionStorage.getItem(k) },
        prefersReducedMotion(),
      ),
  );
  return (
    <>
      {intro && <DeveloperIntro />}
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
