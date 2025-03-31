
import React from 'react';

const BlogSection: React.FC = () => {
  return (
    <div>
      <h3 className="text-lg font-medium mb-4">Latest Blog Posts</h3>
      <div className="flex flex-col space-y-4">
        <div className="flex items-start">
          <div className="w-28 h-20 bg-gray-100 rounded-md flex-shrink-0"></div>
          <div className="ml-4">
            <h4 className="font-medium">Modern Web Development in 2023</h4>
            <p className="text-sm text-gray-500 mt-1">May 15, 2023</p>
          </div>
        </div>
        
        <div className="flex items-start">
          <div className="w-28 h-20 bg-gray-100 rounded-md flex-shrink-0"></div>
          <div className="ml-4">
            <h4 className="font-medium">The Future of React</h4>
            <p className="text-sm text-gray-500 mt-1">April 28, 2023</p>
          </div>
        </div>
      </div>
      <button className="mt-4 text-xs flex items-center text-gray-600">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
        Read all posts
      </button>
    </div>
  );
};

export default BlogSection;
