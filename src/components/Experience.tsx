
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
    <div className="relative">
      <h3 className="text-lg font-medium mb-4">My Experience</h3>
      <div className="pl-6 relative">
        <div className="absolute left-1.5 top-0 bottom-0 w-0.5 bg-gray-200 rounded-full"></div>
        {experiences.map((item, index) => (
          <div
            key={index}
            className="mb-6 relative hover:translate-x-1 transition-transform duration-300"
          >
            <div className="absolute -left-6 top-1.5 bg-black w-3 h-3 rounded-full"></div>
            <div className="p-4 border border-gray-100 rounded-lg shadow-sm bg-white hover:shadow-md transition-shadow duration-300">
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-medium text-base">{item.title}</h4>
                <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">{item.type}</span>
              </div>
              <div className="flex items-center text-gray-500 text-sm mb-1">
                <span className="font-medium text-black">{item.company}</span>
              </div>
              <div className="flex items-center gap-3 text-gray-500 text-xs">
                <div className="flex items-center">
                  <Calendar className="h-3 w-3 mr-1" />
                  <span>{item.period.split(' - ')[0]}</span>
                </div>
                <div className="flex items-center">
                  <MapPin className="h-3 w-3 mr-1" />
                  <span>{item.period.split(' - ')[1]}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Experience;
