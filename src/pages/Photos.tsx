import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, Film } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface Photo {
  id: number;
  url: string;
  title: string;
  story: string;
  date: string;
  color: string;
}

const photos: Photo[] = [
  {
    id: 1,
    url: "https://images.unsplash.com/photo-1736084251103-0104f7e2edee?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Mountain Solitude",
    "story": "High in the peaks, where the air is thin and the silence is profound, the mountains stand as ancient sentinels. This shot captures the raw grandeur of the landscape, a reminder of nature's enduring power and the quiet peace found in its embrace.",
    "date": "2024",
    "color": "#e2e8f0"
  },
  {
    id: 2,
    url: "https://images.unsplash.com/photo-1736084117601-4425fe748df9?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Urban Reflection",
    "story": "The city rain transforms ordinary streets into mirrors of light. In this candid moment, the hustle of urban life pauses for a breath, reflected in the wet pavement. It's a study of contrast—between the fluidity of water and the rigid architecture of the metropolis.",
    "date": "2024",
    "color": "#cbd5e1"
  },
  {
    id: 3,
    url: "https://images.unsplash.com/photo-1694455560154-9b7e03b80f17?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Abstract Leaves",
    "story": "Nature's details often go unnoticed. This macro perspective reveals the intricate veins and vibrant hues of a leaf, a complex map of life usually hidden in plain sight. It challenges us to look closer and appreciate the small masterpieces around us.",
    "date": "2023",
    "color": "#f1f5f9"
  },
  {
    id: 4,
    url: "https://images.unsplash.com/photo-1670865478911-ca5ce379044d?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Golden Hour Silhouette",
    "story": "As the sun dips below the horizon, it paints the world in warm, fleeting gold. This silhouette captures a moment of connection, a human story played out against the vast canvas of the evening sky. It's about the warmth of relationships and the beauty of dusk.",
    "date": "2023",
    "color": "#fed7aa"
  },
  {
    id: 5,
    url: "https://images.unsplash.com/photo-1718299421772-220a50c7db77?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Timeless Architecture",
    "story": "The clock tower stands tall, a witness to the passing of time. The architecture speaks of a different era, where craftsmanship and detail were paramount. It's a blend of history and function, marking moments in the bustling city below.",
    "date": "2024",
    "color": "#e2e8f0"
  },
  {
    id: 6,
    url: "https://images.unsplash.com/photo-1624129061456-8a04235a0391?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Coastal Calm",
    "story": "Where the ocean meets the land, there is a rhythmic conversation. This image captures the serene blue of the coast, a place of retreat and reflection. The vastness of the water invites the mind to wander and find stillness.",
    "date": "2021",
    "color": "#bfdbfe"
  },
  {
    id: 7,
    url: "https://images.unsplash.com/photo-1601720272087-d37a0ffd35e9?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Street Noir",
    "story": "Shadows and light play a game of hide and seek in the city's alleyways. This shot explores the moodier side of street photography, where the unseen is just as important as what is revealed. It's a narrative of mystery and urban intrigue.",
    "date": "2020",
    "color": "#94a3b8"
  },
  {
    id: 8,
    url: "https://images.unsplash.com/photo-1581157709385-469f40b59b04?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Industrial geometric",
    "story": "Lines, shapes, and structures define the industrial landscape. This photograph isolates the geometric beauty found in functional design. It's a celebration of order, symmetry, and the raw aesthetic of construction.",
    "date": "2020",
    "color": "#cbd5e1"
  },
  {
    id: 9,
    url: "https://images.unsplash.com/photo-1736084202533-4763bc6b2aa3?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Misty Morning",
    "story": "The fog rolls in, softening the world and muffling sound. It creates a dreamlike atmosphere where familiar shapes become ghosts. This image is about the quiet magic of early mornings, before the world fully wakes up.",
    "date": "2024",
    "color": "#f1f5f9"
  },
  {
    id: 10,
    url: "https://images.unsplash.com/photo-1692367725833-032abb79d56a?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "The Path Forward",
    "story": "A simple dirt path leading towards a grassy hill. It represents the journey, the unknown destination, and the invitation to explore. The composition draws the eye forward, asking the viewer to step into the frame and walk.",
    "date": "2023",
    "color": "#dcfce7"
  },
    {
    id: 11,
    url: "https://images.unsplash.com/photo-1671040060085-b0b06c3a320f?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Winter's Chill",
    "story": "A cold, crisp day where the air bites and the light is sharp. This photo captures the essence of winter—the dormant trees, the pale sky, and the quiet resilience of the natural world waiting for spring.",
    "date": "2023",
    "color": "#f8fafc"
  },
    {
    id: 12,
    url: "https://images.unsplash.com/photo-1659547677552-e09423b75f86?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.1.0",
    "title": "Summer Vibes",
    "story": "Warmth, light, and vibrant color. This image embodies the carefree spirit of summer. It's a snapshot of a moment filled with energy and the joy of being outdoors, soaking in the sun.",
    "date": "2022",
    "color": "#ffedd5"
  }
];

const Photos = () => {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isCinematic, setIsCinematic] = useState(false);

  return (
    <div
      className="min-h-screen p-4 md:p-12 overflow-x-hidden flex flex-col items-center bg-[#fafafa] modern-grid-bg"
    >
      {/* Book Container */}
      <div
        className="relative max-w-7xl w-full bg-[#fdfdfd] shadow-2xl overflow-hidden min-h-[90vh] rounded-sm"
        style={{
          boxShadow: '0 20px 50px -12px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(0,0,0,0.02)',
        }}
      >
        <div className="p-8 md:p-16 relative z-0">
          <header className="mb-16 relative flex flex-col md:flex-row md:items-end justify-between gap-6 pb-8 border-b-2 border-orange-100/50">
            <div>
              <h1 className="text-5xl md:text-7xl font-serif font-bold tracking-tight text-[#2a2a2a] mb-4">
                Photos by Me
              </h1>
              <p className="text-lg md:text-xl text-gray-600 font-serif italic max-w-2xl">
                "A collection of moments frozen in time, preserved in this digital archive."
              </p>
            </div>

            <div className="flex items-center space-x-3 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-full shadow-sm border border-orange-100">
              <Switch
                id="cinematic-mode"
                checked={isCinematic}
                onCheckedChange={setIsCinematic}
              />
              <Label htmlFor="cinematic-mode" className="text-sm font-medium text-gray-700 cursor-pointer flex items-center gap-2">
                <Film className="w-4 h-4" />
                Vintage Film Mode
              </Label>
            </div>
          </header>

          <div className="columns-1 md:columns-2 lg:columns-3 gap-12 space-y-12 pb-20">
            {photos.map((photo, index) => (
              <div key={photo.id} className="break-inside-avoid pt-2 pl-2">
                <motion.div
                  layoutId={`card-${photo.id}`}
                  onClick={() => setSelectedId(photo.id)}
                  className="cursor-pointer transition-transform duration-300 relative group"
                  whileHover={{
                    scale: 1.03,
                    rotate: 0,
                    zIndex: 20,
                  }}
                  initial={{ rotate: Math.random() * 4 - 2 }}
                  animate={{ rotate: Math.random() * 4 - 2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className={`p-3 pb-10 transition-all duration-300 h-full relative ${
                    isCinematic
                      ? 'bg-[#f0e6d2] vintage-texture shadow-[2px_4px_8px_rgba(0,0,0,0.3)]'
                      : 'bg-white shadow-[0_4px_6px_-1px_rgba(0,0,0,0.1),0_2px_4px_-1px_rgba(0,0,0,0.06)] group-hover:shadow-2xl'
                  }`}>
                    {/* Thumbpin Effect */}
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full shadow-md z-10 thumbpin" />

                    <motion.div
                      className={`aspect-[4/5] overflow-hidden bg-gray-100 mb-4 relative ${isCinematic ? 'film-grain sepia-[0.1]' : ''}`}
                    >
                      <motion.img
                        layoutId={`image-${photo.id}`}
                        src={photo.url}
                        alt={photo.title}
                        className={`w-full h-full object-cover transition-all duration-500 ${
                          isCinematic
                            ? 'contrast-[1.1] brightness-[0.9] saturate-[0.8] sepia-[0.2]'
                            : 'filter grayscale-[10%] group-hover:grayscale-0'
                        }`}
                      />
                      {isCinematic && (
                        <div className="absolute inset-0 bg-gradient-to-tr from-black/20 to-transparent mix-blend-overlay pointer-events-none" />
                      )}
                    </motion.div>
                    <div className={`font-handwriting text-2xl absolute bottom-3 left-4 rotate-[-1deg] flex items-center gap-2 ${
                      isCinematic ? 'text-[#3d3838] opacity-90' : 'text-gray-800'
                    }`}>
                       {photo.title}
                    </div>
                  </div>
                </motion.div>
              </div>
            ))}
          </div>

          <AnimatePresence>
            {selectedId && (
              <div className="fixed inset-0 z-50 flex items-center justify-center px-4 pointer-events-none">
                 <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setSelectedId(null)}
                  className="fixed inset-0 bg-black/80 backdrop-blur-md pointer-events-auto"
                />

                <motion.div
                  className="bg-[#fdfdfd] w-full max-w-5xl h-[85vh] md:h-auto md:max-h-[90vh] shadow-2xl overflow-hidden relative flex flex-col md:flex-row pointer-events-auto rounded-sm"
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedId(null);
                    }}
                    className="absolute top-4 right-4 z-20 p-2 bg-black/5 hover:bg-black/10 rounded-full transition-colors"
                  >
                    <X className="w-6 h-6 text-gray-800" />
                  </button>

                  {/* Left Side - Image */}
                  <div className="w-full md:w-3/5 h-[50%] md:h-auto bg-black/5 relative p-8 md:p-12 flex items-center justify-center border-r border-black/5">
                     <motion.div
                        layoutId={`card-${selectedId}`}
                        className="bg-white p-4 shadow-xl rotate-1 w-full max-w-md relative"
                     >
                        {/* Thumbpin for expanded view too */}
                         <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full shadow-md z-10 thumbpin" />
                        <motion.div className={`w-full h-full relative overflow-hidden aspect-[4/5] ${isCinematic ? 'film-grain' : ''}`}>
                          <motion.img
                            layoutId={`image-${selectedId}`}
                            src={photos.find(p => p.id === selectedId)?.url}
                            alt="Selected"
                            className={`w-full h-full object-cover ${
                              isCinematic
                              ? 'contrast-[1.1] brightness-[0.9] saturate-[0.8] sepia-[0.2]'
                              : ''
                            }`}
                          />
                           {isCinematic && (
                            <div className="absolute inset-0 bg-gradient-to-tr from-black/20 to-transparent mix-blend-overlay pointer-events-none" />
                          )}
                        </motion.div>
                     </motion.div>
                  </div>

                  {/* Right Side - Story */}
                  <div className="w-full md:w-2/5 p-8 md:p-12 flex flex-col justify-center">
                    {photos.map(photo => {
                      if (photo.id !== selectedId) return null;
                      return (
                        <motion.div
                          key={photo.id}
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.2, duration: 0.4 }}
                        >
                           <h2 className="text-4xl md:text-5xl font-bold mb-4 font-handwriting text-[#2a2a2a]">
                            {photo.title}
                          </h2>
                          <span className="inline-block px-3 py-1 bg-orange-100 text-xs font-bold tracking-widest text-orange-800 uppercase rounded-sm mb-8">
                            Captured in {photo.date}
                          </span>

                          <div className="space-y-6">
                              <p className="text-xl leading-relaxed text-gray-800 font-serif italic">
                              "{photo.story}"
                              </p>
                          </div>

                          <div className="mt-12 pt-6 border-t border-black/10">
                            <a
                              href={photo.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-2 text-sm font-bold tracking-widest uppercase text-gray-500 hover:text-orange-700 transition-colors group"
                            >
                              Open Original
                              <ExternalLink className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                            </a>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </motion.div>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&display=swap');

        .font-handwriting {
          font-family: 'Caveat', cursive;
        }
        .font-serif {
          font-family: 'Playfair Display', serif;
        }

        .modern-grid-bg {
          background-color: #fafafa;
          background-image:
            linear-gradient(to right, #e5e5e5 1px, transparent 1px),
            linear-gradient(to bottom, #e5e5e5 1px, transparent 1px);
          background-size: 40px 40px;
          mask-image: radial-gradient(ellipse at center, black 60%, transparent 100%);
        }

        .thumbpin {
          background: radial-gradient(circle at 30% 30%, #e74c3c, #c0392b);
          box-shadow: 1px 1px 3px rgba(0,0,0,0.3);
        }

        .film-grain::after {
          content: "";
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.5'/%3E%3C/svg%3E");
          opacity: 0.5;
          mix-blend-mode: overlay;
          z-index: 20;
        }

        .vintage-texture {
          background-image: url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.5' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.08'/%3E%3C/svg%3E");
          box-shadow:
            1px 1px 3px rgba(0,0,0,0.05) inset, /* Inner bevel */
            2px 4px 10px rgba(0,0,0,0.2); /* Drop shadow */
        }
      `}</style>
    </div>
  );
};

export default Photos;
