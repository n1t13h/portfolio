
import React from 'react';

interface BrowserFrameProps {
  children: React.ReactNode;
}

const BrowserFrame: React.FC<BrowserFrameProps> = ({ children }) => {
  return (
    <div className="bg-white rounded-lg overflow-hidden shadow-md max-w-5xl mx-auto">
      <div className="bg-gray-100 px-4 py-2 flex items-center border-b">
        <div className="flex space-x-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
        </div>
        <div className="ml-4 flex">
          <button className="p-1">
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button className="p-1">
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
        <div className="mx-auto flex-grow max-w-lg">
          <div className="bg-white rounded-md flex items-center justify-center w-full px-3 py-1 text-sm text-gray-500">
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            johndoe.dev
          </div>
        </div>
      </div>
      <div className="p-4 bg-gray-50 min-h-[calc(100vh-4rem)]">
        {children}
      </div>
    </div>
  );
};

export default BrowserFrame;
