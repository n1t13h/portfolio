import { useState } from "react";
import { Link } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { CursorStack } from "./CursorStack";
import type { ResolvedCollection } from "@/data/photos";

export function CollectionRows({ collections }: { collections: ResolvedCollection[] | undefined }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const current = collections?.find((c) => c.slug === hovered);

  if (!collections) {
    return (
      <div data-testid="rows-loading">
        {[0, 1, 2].map((i) => (
          <div key={i} className="border-t border-[#e7e7e7] py-[26px] last:border-b">
            <Skeleton className="h-10 w-2/3 rounded-md bg-[#f1f1f0]" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="group/rows relative">
        {collections.map((c, i) => (
          <Link
            key={c.slug}
            to={`/photos/${c.slug}`}
            onMouseEnter={() => setHovered(c.slug)}
            onMouseLeave={() => setHovered(null)}
            onFocus={() => setHovered(c.slug)}
            onBlur={() => setHovered(null)}
            className="group/row grid grid-cols-[32px_1fr_auto] items-baseline gap-y-1 border-t border-[#e7e7e7] py-[26px] transition-opacity duration-300 motion-reduce:transition-none last:border-b group-hover/rows:[&:not(:hover)]:opacity-30 sm:grid-cols-[60px_1fr_90px_70px] md:grid-cols-[60px_1fr_260px_90px_70px]"
          >
            <span className="font-mono text-xs text-[#9a9a9a]">{String(i + 1).padStart(2, "0")}</span>
            <span className="text-[clamp(30px,3.2vw,52px)] font-medium leading-none tracking-[-0.045em] transition-transform duration-500 ease-out group-hover/row:translate-x-[10px] motion-reduce:transition-none motion-reduce:group-hover/row:translate-x-0">
              {c.title}
            </span>
            <span className="col-start-2 hidden text-[15px] text-[#6b6b6b] md:col-start-auto md:block">{c.place}</span>
            <span className="text-right font-mono text-xs text-[#9a9a9a]">{c.photos.length} frames</span>
            <span className="hidden text-right font-mono text-xs text-[#9a9a9a] sm:block">{c.year}</span>
          </Link>
        ))}
      </div>
      <CursorStack photos={current?.covers ?? []} active={!!current} />
    </>
  );
}
