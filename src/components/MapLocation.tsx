
import React from 'react';
import { MapPin } from 'lucide-react';

const MapLocation: React.FC = () => {
  return (
    <div>
      <div className="relative rounded-lg overflow-hidden h-48 w-full bg-gray-50 flex items-center justify-center border border-gray-100">
        <div className="absolute inset-0">
          {/* Simple map background with grid lines */}
          <div className="w-full h-full bg-white">
            <div className="absolute inset-0" style={{
              backgroundImage: 'linear-gradient(to right, #e5e7eb 1px, transparent 1px), linear-gradient(to bottom, #e5e7eb 1px, transparent 1px)',
              backgroundSize: '20px 20px'
            }}></div>
          </div>
        </div>
        <div className="relative bg-white bg-opacity-80 p-4 rounded-lg shadow-sm text-center">
          <div className="bg-black rounded-full w-8 h-8 flex items-center justify-center mx-auto mb-2">
            <MapPin className="h-5 w-5 text-white" />
          </div>
          <div className="font-medium">Mumbai, India</div>
          <p className="text-sm text-gray-500 mt-1">Currently based here</p>
        </div>
      </div>
      <div className="mt-2 flex justify-between items-center">
        <span className="text-sm text-gray-500">Location</span>
        <button className="text-xs px-3 py-1 bg-black text-white rounded-full hover:bg-gray-800 transition-colors">
          Contact me
        </button>
      </div>
    </div>
  );
};

export default MapLocation;
