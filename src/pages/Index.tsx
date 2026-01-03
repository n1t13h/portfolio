import React, { useState } from "react";
import { Navbar } from "@/components/Navbar";
import ProjectsSection from "@/components/ProjectsSection";
import Experience from "@/components/Experience";
import Skills from "@/components/Skills";
import profilePhoto from "@/assets/final.png";
import { motion, AnimatePresence } from "framer-motion";

const Index: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-foreground relative selection:bg-black selection:text-white dark:selection:bg-white dark:selection:text-black font-['Space_Grotesk']">
      <Navbar />

      {/* HERO: The Manifest - Centered Layout with Kinetic Motion */}
      <section className="min-h-screen flex flex-col justify-center px-4 md:px-8 max-w-[1920px] mx-auto pt-20">

        <div className="flex flex-col md:flex-row justify-between items-center md:items-end gap-12 w-full">
           <div className="flex-1 w-full relative z-10">
              {/* Kinetic Typography */}
              <motion.div
                initial={{ opacity: 0, y: 100 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                className="relative"
              >
                  <h1 className="text-[14vw] leading-[0.8] font-bold tracking-tighter uppercase text-foreground mix-blend-exclusion hover:text-primary transition-colors duration-500 cursor-default">
                    <span className="block overflow-hidden">
                        <motion.span
                            initial={{ y: "100%" }}
                            animate={{ y: "0%" }}
                            transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                            className="block"
                        >
                            NITISH
                        </motion.span>
                    </span>
                    <span className="block overflow-hidden">
                        <motion.span
                            initial={{ y: "100%" }}
                            animate={{ y: "0%" }}
                            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                            className="block"
                        >
                            PATEL
                        </motion.span>
                    </span>
                  </h1>
              </motion.div>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6, duration: 1 }}
                className="font-mono text-sm md:text-lg text-muted-foreground max-w-xl uppercase tracking-widest mt-8 ml-2"
              >
                // Software Craftperson<br/>
              </motion.p>
           </div>

           {/* Editorial Image Placement */}
           <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.4, ease: "easeOut" }}
              className="hidden md:block mb-8 relative"
           >
             <div className="w-[400px] h-[500px] grayscale hover:grayscale-0 transition-all duration-700 ease-in-out relative overflow-hidden group">
               <img src={profilePhoto} alt="Profile" className="w-full h-full object-cover scale-110 hover:scale-100 transition-transform duration-1000" />
               <div className="absolute inset-0 border border-border opacity-20 group-hover:border-primary/50 transition-colors" />
             </div>

             {/* Studio Meta Data */}
             <div className="absolute -left-12 bottom-12 -rotate-90 origin-left">
                <span className="font-mono text-xs text-muted-foreground uppercase tracking-widest group-hover:text-primary transition-colors">EST. 2024</span>
             </div>
           </motion.div>
        </div>
        <div className="border-t border-border mt-12 w-full" />
      </section>

      {/* SELECTED WORKS: The Archive */}
      <section id="work" className="px-4 md:px-8 max-w-[1920px] mx-auto mb-32">
        <ProjectsSection />
      </section>

      {/* INFO GRID: The Specs */}
      <section id="about" className="px-4 md:px-8 max-w-[1920px] mx-auto mb-32">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-32">

          {/* LEFT: Experience List */}
          <div>
            <div className="flex justify-between items-end mb-8 border-b border-border pb-4">
               <h3 className="text-sm font-mono text-muted-foreground">EXPERIENCE LOG</h3>
               <span className="text-sm font-mono text-muted-foreground">(03)</span>
            </div>

            <Experience />
          </div>

          {/* RIGHT: Stack & Bio */}
          <div className="flex flex-col gap-16">
            <div>
               <div className="flex justify-between items-end mb-8 border-b border-border pb-4">
                  <h3 className="text-sm font-mono text-muted-foreground">BIO_DATA</h3>
               </div>
               <p className="text-2xl md:text-3xl font-light leading-snug text-foreground/90">
                 I build accessible, pixel-perfect, and performant web experiences.
                 Currently obsessed with <span className="underline decoration-1 underline-offset-4 decoration-primary/50">Agentic AI</span> and <span className="underline decoration-1 underline-offset-4 decoration-primary/50">DeFi Protocols</span>.
               </p>
            </div>


          </div>

        </div>

        <div className="mt-16 md:mt-32">
           <div className="flex justify-between items-end mb-8 border-b border-border pb-4">
              <h3 className="text-sm font-mono text-muted-foreground">TECH_STACK</h3>
           </div>
           <Skills />
        </div>
      </section>

      {/* FOOTER: The Connection */}
      <section id="contact" className="px-4 md:px-8 pt-20 pb-10 border-t border-border">
         <div className="flex flex-col items-center justify-center text-center py-20">
            <h2 className="text-[8vw] md:text-[6vw] font-bold leading-none tracking-tighter hover:text-primary transition-colors cursor-pointer text-foreground">
              <a href="mailto:contact@ntshptl.in">LET'S TALK</a>
            </h2>
            <div className="flex gap-8 mt-12 font-mono text-sm uppercase text-foreground">
               <a href="https://github.com/nitishpatel/" className="hover:text-primary transition-colors">Github</a>
               <a href="https://linkedin.com/in/ntshptl/" className="hover:text-primary transition-colors">LinkedIn</a>
               <a href="https://twitter.com" className="hover:text-primary transition-colors">Twitter</a>
               <a href="https://drive.google.com/file/d/1lJnzel5i3I2sT_K-zKzNwnAngtSkR-f4/view?usp=sharing" className="hover:text-primary transition-colors">Resume</a>
            </div>
         </div>

         <div className="flex justify-between font-mono text-[10px] text-muted-foreground uppercase pt-12">
            <span>© 2024 Nitish Patel</span>
            <span>SYSTEM_STATUS: ONLINE</span>
         </div>
      </section>

    </div>
  );
};

export default Index;
