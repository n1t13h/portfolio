import React from 'react';

const projects = [
  {
    id: "01",
    title: "INSURANCE BROKER",
    year: "2024",
    tags: ["AWS", "SERVERLESS"],
    description: "EHB Portal for leading insurance broker"
  },
  {
    id: "02",
    title: "DOC ATTESTATION",
    year: "2023",
    tags: ["BLOCKCHAIN", "NEXT.JS"],
    description: "Decentralized document verification"
  },
  {
    id: "03",
    title: "AGENTIC RAG",
    year: "2023",
    tags: ["AI", "VECTOR DB"],
    description: "Autonomous reasoning engine"
  },
  {
    id: "04",
    title: "LIQUID STAKING",
    year: "2022",
    tags: ["ETH", "SOLIDITY"],
    description: "DeFi protocol for asset staking"
  }
];

const ProjectsSection: React.FC = () => {
  return (
    <div className="w-full relative">
      <div className="flex justify-between items-end mb-12 border-b border-border pb-4">
         <h3 className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Selected Works</h3>
         <span className="text-sm font-mono text-muted-foreground">(04)</span>
      </div>

      <div className="flex flex-col">
        {projects.map((project) => (
          <div
            key={project.id}
            className="group relative border-t border-border py-12 md:py-16 transition-colors duration-300 hover:bg-primary hover:text-primary-foreground cursor-pointer"
          >
            <div className="flex flex-col md:flex-row justify-between items-start md:items-baseline gap-4 px-4 md:px-0">
               <div className="flex items-baseline gap-6 md:w-1/3">
                 <span className="font-mono text-xs text-muted-foreground group-hover:text-primary-foreground/60">/{project.id}</span>
                 <h4 className="text-4xl md:text-6xl font-bold tracking-tighter uppercase font-['Space_Grotesk'] group-hover:translate-x-4 transition-transform duration-500">{project.title}</h4>
               </div>

               <div className="md:w-1/3 text-left hidden md:block">
                  <p className="font-mono text-xs text-muted-foreground group-hover:text-primary-foreground/60 uppercase">{project.description}</p>
               </div>

               <div className="md:w-1/3 flex justify-end gap-2 items-center">
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    {project.tags.map((tag, i) => (
                      <span key={i} className="text-[10px] border border-current rounded-full px-2 py-0.5 font-mono uppercase bg-transparent">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <span className="font-mono text-xs hidden md:inline-block group-hover:font-bold">{project.year}</span>
               </div>
            </div>
          </div>
        ))}
        <div className="border-t border-border" />
      </div>
    </div>
  );
};

export default ProjectsSection;
