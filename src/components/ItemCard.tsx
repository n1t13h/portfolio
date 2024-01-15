import { motion, useAnimation } from "framer-motion";
import { useEffect } from "preact/hooks";

import { useInView } from "react-intersection-observer";

type ItemCardProps = {
  title: string;
  description?: string;
  image?: string;
  url?: string;
  tags?: string[];
};

const ItemCard = ({ title, description, url, tags }: ItemCardProps) => {
  const controls = useAnimation();
  const [ref, inView] = useInView();

  useEffect(() => {
    if (inView) {
      controls.start("visible");
    }
  }, [controls, inView]);

  return (
    <motion.div
      ref={ref as any}
      animate={controls}
      initial="hidden"
      transition={{ duration: 1 }}
      variants={{
        visible: { opacity: 1, scale: 1 },
        hidden: { opacity: 0, scale: 0 },
      }}
    >
      <div className="item-card flex flex-col bg-white border border-t-4 border-t-orange-500 shadow-sm rounded-xl dark:bg-slate-900 dark:border-gray-700 dark:border-t-secondary-500 dark:shadow-slate-700/[.7]">
        <div className="p-4 md:p-5">
          <h3 className="text-lg font-bold text-gray-800 dark:text-white">
            {title}
          </h3>
          <p className="mt-2 text-gray-500 dark:text-gray-400">{description}</p>
          {/* Render HashTags */}
          <div className="flex flex-wrap mt-4">
            {tags &&
              tags.map((tag, index) => (
                <span key={index} className="tag">
                  #{tag}
                </span>
              ))}
          </div>
          {url && (
            <a
              class="mt-3 inline-flex items-center gap-x-1 text-sm font-semibold rounded-lg border border-transparent text-blue-600 hover:text-blue-800 disabled:opacity-50 disabled:pointer-events-none dark:text-blue-500 dark:hover:text-blue-400 dark:focus:outline-none dark:focus:ring-1 dark:focus:ring-gray-600"
              href={url}
              target="_blank"
            >
              Check it out
              <svg
                class="flex-shrink-0 w-4 h-4"
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="m9 18 6-6-6-6" />
              </svg>
            </a>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default ItemCard;
