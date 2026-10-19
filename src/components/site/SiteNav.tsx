import { Link, NavLink } from "react-router-dom";
import { Menu } from "lucide-react";
import { Sheet, SheetClose, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { site } from "@/content/site";

const sections = [
  { label: "Work", to: "/#work" },
  { label: "About", to: "/#about" },
  { label: "Experience", to: "/#experience" },
];

const linkCls = "text-[15px] text-[#444] transition-colors hover:text-ink";

export function SiteNav() {
  return (
    <nav className="sticky top-0 z-10 bg-white/85 backdrop-blur-[14px]">
      <div className="mx-auto grid h-16 max-w-[1520px] grid-cols-[1fr_auto_1fr] items-center px-4 sm:px-7">
        <Link to="/" className={`${linkCls} inline-flex min-h-11 items-center`}>Nitish</Link>

        <div className="hidden gap-[46px] md:flex">
          {sections.map((s) => (
            <Link key={s.label} to={s.to} className={linkCls}>{s.label}</Link>
          ))}
          <NavLink
            to="/photos"
            className={({ isActive }) =>
              `${linkCls} ${isActive ? "underline underline-offset-[6px] text-ink" : ""}`
            }
          >
            Photography
          </NavLink>
        </div>

        <div className="col-start-3 flex items-center justify-self-end gap-[18px]">
          <a href={site.links.resume} target="_blank" rel="noreferrer" className={`${linkCls} hidden md:inline`}>Résumé</a>
          <Link to="/#contact" className={`${linkCls} hidden md:inline`}>Contact</Link>
          <Sheet>
            <SheetTrigger aria-label="Menu" className="-mr-3 inline-flex h-11 w-11 items-center justify-center md:hidden">
              <Menu className="h-5 w-5" />
            </SheetTrigger>
            <SheetContent side="right" aria-describedby={undefined}>
              <SheetTitle className="sr-only">Menu</SheetTitle>
              <div className="mt-8 flex flex-col gap-5 text-lg">
                {sections.map((s) => (
                  <SheetClose asChild key={s.label}>
                    <Link to={s.to}>{s.label}</Link>
                  </SheetClose>
                ))}
                <SheetClose asChild>
                  <NavLink to="/photos">Photography</NavLink>
                </SheetClose>
                <div className="my-1 h-px bg-line" />
                <a href={site.links.resume} target="_blank" rel="noreferrer">Résumé</a>
                <SheetClose asChild>
                  <Link to="/#contact">Contact</Link>
                </SheetClose>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  );
}
