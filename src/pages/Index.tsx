import React, { useState } from "react";
import BrowserFrame from "@/components/BrowserFrame";
import BentoGrid from "@/components/BentoGrid";
import BentoItem from "@/components/BentoItem";
import Experience from "@/components/Experience";
import ProjectsSection from "@/components/ProjectsSection";
import BlogSection from "@/components/BlogSection";
import MapLocation from "@/components/MapLocation";
import Skills from "@/components/Skills";
import { Button } from "@/components/ui/button";
import { Share2, Github, Linkedin, FileText } from "lucide-react";
import { toast } from "@/components/ui/use-toast";
import profilePhoto from "@/assets/final.png";

const Index: React.FC = () => {
  const [isGenerating, setIsGenerating] = useState(false);

  const handleShareBusinessCard = async () => {
    setIsGenerating(true);
    try {
      // In a real app, this would use html-to-image or similar
      // For now, we'll simulate the generation
      await new Promise((resolve) => setTimeout(resolve, 1500));

      toast({
        title: "Business card generated!",
        description:
          "Your business card has been copied to clipboard and can be shared.",
      });
    } catch (error) {
      toast({
        title: "Error generating business card",
        description: "Please try again later.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div>
      <div className="max-w-5xl mx-auto px-4 py-8">
        <header className="mb-12">
          {/* Top header: logo/email and social icons */}
          <div className="flex flex-col md:flex-row justify-between items-center mb-8">
            <div className="flex items-center mb-4 md:mb-0">
              <div className="h-10 w-10 bg-black rounded flex items-center justify-center text-white">
                <span>NP</span>
              </div>
              <span className="ml-2 text-gray-800 text-sm sm:text-base">
                nitishp.dev@gmail.com
              </span>
            </div>

            <div className="flex items-center space-x-3">
              <a
                href="https://github.com/nitishpatel/"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <Github className="h-5 w-5" />
              </a>
              <a
                href="https://linkedin.com/in/ntshptl/"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <Linkedin className="h-5 w-5" />
              </a>
              <a
                href="https://drive.google.com/file/d/19l2EDXou4EldioKaLLhomuMb7NBt2XMu/view?usp=drive_link"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
              >
                <FileText className="h-4 w-4" />
                Resume
              </a>
            </div>
          </div>

          {/* Main introduction */}
          <div className="flex flex-col md:flex-row md:items-end mb-6">
            <div className="flex-grow">
              <div className="flex flex-col sm:flex-row items-center mb-2">
                <h1 className="text-3xl sm:text-4xl font-bold mr-3 text-center sm:text-left">
                  Hi, I'm
                </h1>
                <div className="relative">
                  <img
                    src={profilePhoto}
                    alt="Profile"
                    className="w-12 h-12 rounded-full object-cover transition-transform duration-300 hover:scale-125"
                  />
                </div>
                <h1 className="text-3xl sm:text-4xl font-bold ml-0 sm:ml-2 mt-2 sm:mt-0 text-center sm:text-left">
                  Nitish Patel!
                </h1>
              </div>

              <div className="text-xl sm:text-2xl text-gray-500 mb-2 text-center md:text-left">
                I'm a{" "}
                <span className="text-black font-medium">
                  Full Stack Developer
                </span>{" "}
                specialized in
              </div>
              <div className="text-[#FF6D0A] text-2xl sm:text-3xl font-medium mb-4 text-center md:text-left">
                AI, Web3, React, Django & MERN.
              </div>

              <div className="inline-block bg-gray-100 rounded-full px-4 py-1.5 text-sm mb-6">
                <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                Open to work
              </div>
            </div>
          </div>

          <p className="text-lg max-w-2xl mx-auto md:mx-0 text-center md:text-left mb-6">
  Feel free to explore my portfolio and reach out—I'd love to connect!
</p>


          <div className="mt-6 flex justify-center md:justify-start">
            <Button className="bg-black hover:bg-gray-800 text-white rounded-full px-6 py-2">
              Book a call
            </Button>
          </div>
        </header>

        <BentoGrid className="mb-12">
          <BentoItem >
            <Skills />
          </BentoItem>

          <BentoItem colSpan={2}>
            <Experience />
          </BentoItem>

          <BentoItem>
            <ProjectsSection />
          </BentoItem>

          <BentoItem colSpan={2}>
            <BlogSection />
          </BentoItem>

          <BentoItem colSpan={3}>
            <MapLocation />
          </BentoItem>
        </BentoGrid>

        <div className="mt-16 mb-8 flex justify-center">
          <Button
            variant="outline"
            className="group border-dashed hover:border-solid flex items-center gap-2 rounded-full py-2 px-6"
            onClick={handleShareBusinessCard}
            disabled={isGenerating}
          >
            <Share2 className="h-4 w-4 group-hover:rotate-12 transition-transform" />
            {isGenerating ? "Generating..." : "Share my business card"}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Index;
