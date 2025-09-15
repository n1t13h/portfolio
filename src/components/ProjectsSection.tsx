import React, { useState } from 'react';
import ReactDOM from 'react-dom';

const projects = [
  {
    title: "Insurance Broker",
    description:
      "Created EHB Portal for an leading insurance broker in India",
    tags: ["Insurance", "EHB", "AWS Serverless Backend"],
  },
  {
    title: "Document Attestation",
    description:
      "A blockchain based document attestation system built using Open Attestation",
    tags: ["Blockchain", "Open Attestation", "Account Abstraction"],
  },
  {
    title: "Agentic RAG",
    description: "An AI agent that can answer questions about a document or Database",
    tags: ["AI", "LangChain", "Vector DB"],
  },
  {
    title: "Liquid Staking",
    description:
      "A liquid staking protocol that allows users to stake their assets and receive a liquid token in return",
    tags: ["Blockchain", "Liquid Staking", "Ethereum"],
  }

];

const ProjectsSection: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const renderProjects = (endpoint: number = projects.length) => (
    <div className="space-y-4">
      {projects.slice(0, endpoint).map((project, index) => (
        <div
          key={index}
          className="border border-gray-200 p-4 rounded-lg hover:shadow-md transition-shadow"
        >
          <div className="font-medium">{project.title}</div>
          <p className="text-sm text-gray-500 mt-1">{project.description}</p>
          <div className="flex gap-2 mt-2 flex-wrap">
            {project.tags.map((tag, idx) => (
              <span
                key={idx}
                className="bg-gray-100 text-xs px-2 py-1 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div>
      <h3 className="text-lg font-medium mb-4">My Projects</h3>
      {renderProjects(2)}
      <button
        onClick={() => setIsModalOpen(true)}
        className="mt-4 text-xs flex items-center text-gray-600"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4 mr-1"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
          />
        </svg>
        View all projects
      </button>

      {/* Modal via Portal */}
      {isModalOpen &&
        ReactDOM.createPortal(
          <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-lg w-full max-h-[70vh] overflow-y-auto shadow-lg">
              <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2">
                <h3 className="text-lg font-medium">My Projects</h3>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="text-gray-600 text-2xl font-bold"
                >
                  &times;
                </button>
              </div>
              {renderProjects()}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
};

export default ProjectsSection;
