import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function ScrollToHash() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const behavior: ScrollBehavior = reduce ? "auto" : "smooth";
    const id = hash ? decodeURIComponent(hash.slice(1)) : "";
    const el = id ? document.getElementById(id) : null;
    if (el) el.scrollIntoView({ behavior });
    else window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname, hash]);

  return null;
}
