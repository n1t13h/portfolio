import { Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { SiteNav } from "@/components/site/SiteNav";
import { SiteFooter } from "@/components/site/SiteFooter";
import { CollectionRows } from "@/components/photos/CollectionRows";
import { ContactSheet } from "@/components/photos/ContactSheet";
import { Lightbox, useLightboxParam } from "@/components/photos/Lightbox";
import { Skeleton } from "@/components/ui/skeleton";
import { getCollections, getPhotos } from "@/data/photos";
import { site } from "@/content/site";

const Photos = () => {
  const { open } = useLightboxParam();
  const collections = useQuery({ queryKey: ["collections"], queryFn: getCollections });
  const photos = useQuery({ queryKey: ["photos"], queryFn: getPhotos });

  return (
    <>
      <SiteNav />
      <main data-testid="page-photos" className="mx-auto max-w-[1520px] px-4 sm:px-7">
        <section className="pb-[50px] pt-[38px]">
          <h1 className="text-[clamp(36px,3.4vw,54px)] font-medium leading-[1.05] tracking-[-0.045em]">
            Photographs
          </h1>
          <p className="mt-[14px] max-w-[720px] text-[clamp(17px,1.35vw,21px)] text-[#6b6b6b]">
            {site.photos.intro.split(site.photos.camera).map((part, i) => (
              <Fragment key={i}>
                {i > 0 && <span className="text-ink">{site.photos.camera}</span>}
                {part}
              </Fragment>
            ))}
          </p>
        </section>
        <CollectionRows collections={collections.data} />
        <section className="mt-[70px]">
          <h2 className="mb-[22px] text-[17px] font-normal text-[#333]">⁎ Every frame</h2>
          {photos.data ? (
            <ContactSheet photos={photos.data} onOpen={open} />
          ) : (
            <Skeleton className="h-64 w-full rounded-[3px] bg-[#f1f1f0]" />
          )}
        </section>
      </main>
      {photos.data && collections.data && (
        <Lightbox photos={photos.data} collections={collections.data} />
      )}
      <SiteFooter />
    </>
  );
};

export default Photos;
