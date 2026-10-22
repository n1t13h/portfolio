import { Link, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { SiteNav } from "@/components/site/SiteNav";
import { SiteFooter } from "@/components/site/SiteFooter";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  return (
    <>
      <SiteNav />
      <main
        data-testid="page-not-found"
        className="mx-auto max-w-[1520px] bg-white px-4 pb-10 pt-[38px] font-sans text-[#0b0b0b] sm:px-7"
      >
        <p className="pt-16 text-[clamp(24px,2.4vw,36px)] tracking-[-0.03em]">Page not found.</p>
        <Link to="/" className="mb-24 inline-block py-2 text-[15px] text-[#6b6b6b] hover:text-[#0b0b0b]">
          ← Back home
        </Link>
      </main>
      <SiteFooter />
    </>
  );
};

export default NotFound;
