import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Intro } from "@/components/home/Intro";
import { DeveloperIntro } from "./DeveloperIntro";
import { parseIntroVariant } from "./variants";

const noop = () => {};

const prefersReducedMotion = () =>
  typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Picks the intro from `?intro=` on the page's first load. It sits outside <Routes>, so the
 * overlay survives the redirect that `?intro=photos` performs and fades out over the page it
 * opened. An explicit variant always plays (it ignores the once-per-session flag) unless the
 * visitor prefers reduced motion; `photos` still opens the photography page in that case.
 */
export function IntroGate() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [variant] = useState(() => parseIntroVariant(window.location.search));
  const [reduced] = useState(prefersReducedMotion);

  useEffect(() => {
    if (variant === "photos" && !pathname.startsWith("/photos")) {
      navigate("/photos", { replace: true });
    }
    // First load only: later navigation must not re-trigger the redirect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!variant || reduced) return null;
  return variant === "developer" ? <DeveloperIntro /> : <Intro onDone={noop} />;
}
