import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { SiteNav } from "@/components/site/SiteNav";
import { SiteFooter } from "@/components/site/SiteFooter";
import { EssayBlock } from "@/components/photos/EssayBlock";
import { Lightbox, useLightboxParam } from "@/components/photos/Lightbox";
import { Skeleton } from "@/components/ui/skeleton";
import { getCollections } from "@/data/photos";
import { buildEssayBlocks } from "@/data/photos/essayLayout";

const Back = () => (
  <Link to="/photos" className="inline-block py-2 text-[15px] text-[#6b6b6b] hover:text-[#0b0b0b]">
    ← All collections
  </Link>
);

const PhotoCollection = () => {
  const { slug } = useParams();
  const { open } = useLightboxParam();
  const { data: collections, isLoading } = useQuery({ queryKey: ["collections"], queryFn: getCollections });
  const index = collections?.findIndex((c) => c.slug === slug) ?? -1;
  const collection = collections && index >= 0 ? collections[index] : null;
  const next = collections && collection ? collections[(index + 1) % collections.length] : null;

  useEffect(() => {
    if (!collection) return;
    const prev = document.title;
    document.title = `${collection.title} — Photographs — Nitish Patel`;
    return () => {
      document.title = prev;
    };
  }, [collection]);

  useEffect(() => {
    window.scrollTo?.({ top: 0, left: 0, behavior: "instant" });
  }, [slug]);

  const camera = collection?.photos[0]?.exif?.camera;
  const facts: [string, string | number][] = collection
    ? [
        ["Frames", collection.photos.length],
        ["Where", collection.place],
        ...(camera ? [["Camera", camera] as [string, string]] : []),
        ["Year", collection.year],
      ]
    : [];

  return (
    <>
      <SiteNav />
      <main data-testid="page-photo-collection" className="mx-auto max-w-[1520px] px-4 pb-10 pt-[38px] sm:px-7">
        <Back />
        {isLoading && <Skeleton className="mt-6 h-40 w-full rounded-md bg-[#f1f1f0]" />}
        {!isLoading && !collection && (
          <p className="py-24 text-[clamp(24px,2.4vw,36px)] tracking-[-0.03em]">Collection not found.</p>
        )}
        {collection && next && (
          <>
            <section className="grid grid-cols-1 items-end gap-10 pb-[50px] pt-[22px] md:grid-cols-2">
              <h1 className="text-[clamp(44px,5vw,84px)] font-medium leading-[0.98] tracking-[-0.055em]">
                {collection.title}
              </h1>
              <div>
                <p className="text-[clamp(18px,1.5vw,23px)] leading-[1.45] tracking-[-0.02em] text-[#333]">
                  {collection.intro}
                </p>
                <dl className="mt-5 flex flex-wrap gap-x-7 gap-y-3">
                  {facts.map(([label, value]) => (
                    <div key={label}>
                      <dt className="font-mono text-xs uppercase text-[#9a9a9a]">{label}</dt>
                      <dd className="mt-0.5 text-[15px] font-medium tracking-[-0.01em]">{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </section>
            {collection.chapters.map((ch, n) => (
              <section key={ch.title}>
                <div className="mb-[26px] mt-[70px] grid grid-cols-[44px_1fr] items-baseline gap-y-1 border-t border-[#0b0b0b] py-5 sm:grid-cols-[60px_1fr_auto]">
                  <span className="font-mono text-xs text-[#9a9a9a]">{String(n + 1).padStart(2, "0")}</span>
                  <h2 className="text-[26px] font-medium tracking-[-0.035em]">{ch.title}</h2>
                  <span className="col-start-2 text-[15px] text-[#6b6b6b] sm:col-start-auto">{ch.note}</span>
                </div>
                {buildEssayBlocks(ch.photos).map((block, i) => (
                  <EssayBlock key={`${ch.title}-${i}`} block={block} onOpen={open} />
                ))}
              </section>
            ))}
            <Link
              to={`/photos/${next.slug}`}
              aria-label={`Next collection: ${next.title}`}
              className="group mt-10 flex items-baseline justify-between gap-4 border-t border-[#e7e7e7] py-[30px]"
            >
              <span className="font-mono text-xs text-[#9a9a9a]">Next collection</span>
              <span className="text-[clamp(30px,3.2vw,52px)] font-medium tracking-[-0.045em] decoration-2 underline-offset-8 group-hover:underline">
                {next.title} →
              </span>
            </Link>
          </>
        )}
      </main>
      {collections && collection && <Lightbox photos={collection.photos} collections={collections} />}
      <SiteFooter />
    </>
  );
};

export default PhotoCollection;
