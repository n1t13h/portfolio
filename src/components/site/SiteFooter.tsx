import { useEffect, useState } from "react";
import { formatIndiaTime } from "@/lib/time";

export function SiteFooter() {
  const [time, setTime] = useState(() => formatIndiaTime(new Date()));

  useEffect(() => {
    const t = setInterval(() => setTime(formatIndiaTime(new Date())), 30000);
    return () => clearInterval(t);
  }, []);

  return (
    <footer className="mx-auto flex max-w-[1520px] justify-between px-4 pb-7 pt-[60px] text-[13px] text-soft sm:px-7">
      <span>© Nitish Patel</span>
      <span className="font-mono tabular-nums">{time}</span>
    </footer>
  );
}
