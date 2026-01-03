
import { motion } from "framer-motion";
import { Home, User, Briefcase, Mail, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";
import { ModeToggle } from "./mode-toggle";

const navItems = [
  { name: "Home", icon: Home, href: "#home" },
  { name: "Work", icon: Briefcase, href: "#work" },
  { name: "About", icon: User, href: "#about" },
  { name: "Resume", icon: FileText, href: "https://drive.google.com/file/d/1lJnzel5i3I2sT_K-zKzNwnAngtSkR-f4/view?usp=sharing" },
  { name: "Contact", icon: Mail, href: "#contact" },
];

export const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="fixed top-6 left-0 right-0 z-50 flex justify-center pointer-events-none">
      <motion.nav
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className={cn(
          "pointer-events-auto flex items-center gap-2 px-2 py-2 rounded-full border border-border bg-background/80 backdrop-blur-md shadow-lg transition-all duration-300",
          scrolled ? "scale-90 shadow-xl" : "scale-100"
        )}
      >
        {navItems.map((item) => (
          <a
            key={item.name}
            href={item.href}
            className={cn(
              "relative px-4 py-2 text-sm transition-colors group rounded-full",
              item.name === "Resume" ? "text-foreground font-medium" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span className="relative z-10 flex items-center gap-2">
              <item.icon className="w-4 h-4" />
              <span className="hidden sm:inline uppercase font-mono text-xs">{item.name}</span>
            </span>
            <span className="absolute inset-0 rounded-full bg-foreground/5 scale-0 group-hover:scale-100 transition-transform duration-200" />
          </a>
        ))}
        <div className="pl-2 border-l border-border ml-2">
           <ModeToggle />
        </div>
      </motion.nav>
    </div>
  );
};
