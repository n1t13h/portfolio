import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getPhotos } from "@/data/photos";
import { imgUrl } from "@/lib/unsplash";

const HEIGHTS = [150, 200, 130, 180, 160, 210, 140, 190];
const COUNT = 15;

export function LensStrip() {
  const { data } = useQuery({ queryKey: ["photos"], queryFn: getPhotos });
  const photos = data?.slice(0, COUNT) ?? [];

  return (
    <>
      <div className="mb-[22px] flex items-end justify-between gap-4">
        <div className="text-[17px] text-[#333]">⁎ Through my lens</div>
        <Link to="/photos" className="text-[17px] hover:underline">
          See all photographs →
        </Link>
      </div>
      <div data-testid="lens-strip" className="flex min-h-[220px] items-start gap-2 overflow-x-auto pb-[10px] [scrollbar-width:none] sm:overflow-hidden [&::-webkit-scrollbar]:hidden">
        {photos.length === 0 &&
          HEIGHTS.slice(0, 6).map((h, i) => (
            <div
              key={i}
              aria-hidden="true"
              style={{ height: h, width: Math.round(h * 1.5) }}
              className="flex-none rounded-[4px] bg-[#f1f1f0]"
            />
          ))}
        {photos.map((p, i) => {
          const h = HEIGHTS[i % HEIGHTS.length];
          return (
            <Link
              key={p.id}
              to={`/photos?photo=${p.id}`}
              aria-label={`Photo: ${p.title}`}
              style={{ height: h, width: Math.round(h * p.aspectRatio) }}
              className="block flex-none overflow-hidden rounded-[4px] bg-[#f1f1f0] transition-transform duration-[600ms] ease-out hover:-translate-y-2 motion-reduce:transition-none motion-reduce:hover:translate-y-0"
            >
              <img
                src={imgUrl(p.pid, 500)}
                alt=""
                loading="lazy"
                className="block h-full w-full object-cover"
              />
            </Link>
          );
        })}
      </div>
    </>
  );
}
