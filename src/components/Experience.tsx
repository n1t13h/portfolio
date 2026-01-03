
import React from 'react';
import { Calendar, MapPin, Clock } from 'lucide-react';

interface ExperienceItem {
  title: string;
  company: string;
  period: string;
  type: string;
}

const experiences: ExperienceItem[] = [
  {
    title: "Software Craftperson",
    company: "Incubyte",
    period: "Sep 2025 to present - Remote",
    type: "Full time"
  },
  {
    title: "Team lead",
    company: "Yodaplus",
    period: "Apr 2023 to Aug 2025 - Hybrid",
    type: "Full time"
  },
  {
    title: "Software Engineer",
    company: "Yodaplus",
    period: "Jul 2021 to Apr 2023 - Hybrid",
    type: "Full time"
  },
];

const Experience: React.FC = () => {
  return (
    <div className="flex flex-col">
      {experiences.map((item, index) => (
        <div
          key={index}
          className="border-t border-border py-6 transition-colors duration-300 hover:bg-foreground hover:text-background cursor-pointer group"
        >
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2">
            <div>
               <h4 className="font-bold text-xl uppercase tracking-tight">{item.title}</h4>
               <span className="text-sm font-mono text-muted-foreground group-hover:text-background/60">{item.company}</span>
            </div>
            <div className="text-right">
               <span className="font-mono text-xs uppercase block">{item.period}</span>
               <span className="font-mono text-[10px] text-muted-foreground group-hover:text-background/60 uppercase">{item.type}</span>
            </div>
          </div>
        </div>
      ))}
      <div className="border-t border-border" />
    </div>
  );
};

export default Experience;
