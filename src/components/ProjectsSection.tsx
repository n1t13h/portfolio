
import React from 'react';

const ProjectsSection: React.FC = () => {
  return (
    <div>
      <h3 className="text-lg font-medium mb-4">My Projects</h3>
      <div className="space-y-4">
        <div className="border border-gray-200 p-4 rounded-lg hover:shadow-md transition-shadow">
          <div className="font-medium">Portfolio Website</div>
          <p className="text-sm text-gray-500 mt-1">A personal portfolio built with React and Tailwind CSS.</p>
          <div className="flex gap-2 mt-2">
            <span className="bg-gray-100 text-xs px-2 py-1 rounded-full">React</span>
            <span className="bg-gray-100 text-xs px-2 py-1 rounded-full">Tailwind</span>
          </div>
        </div>
        
        <div className="border border-gray-200 p-4 rounded-lg hover:shadow-md transition-shadow">
          <div className="font-medium">E-commerce App</div>
          <p className="text-sm text-gray-500 mt-1">A full-stack e-commerce platform with cart functionality.</p>
          <div className="flex gap-2 mt-2">
            <span className="bg-gray-100 text-xs px-2 py-1 rounded-full">Node.js</span>
            <span className="bg-gray-100 text-xs px-2 py-1 rounded-full">MongoDB</span>
          </div>
        </div>
      </div>
      <button className="mt-4 text-xs flex items-center text-gray-600">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
        View all projects
      </button>
    </div>
  );
};

export default ProjectsSection;
