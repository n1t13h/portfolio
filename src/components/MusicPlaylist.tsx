
import React from 'react';

const MusicPlaylist: React.FC = () => {
  return (
    <div>
      <h3 className="text-lg font-medium mb-4">My music playlist</h3>
      <div className="flex flex-wrap gap-2">
        <div className="relative group">
          <img 
            src="https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=200&h=200" 
            alt="Album cover" 
            className="w-24 h-24 object-cover rounded-lg shadow-sm"
          />
        </div>
        <div className="relative group">
          <img 
            src="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=200&h=200" 
            alt="Album cover" 
            className="w-24 h-24 object-cover rounded-lg shadow-sm"
          />
        </div>
        <div className="relative group">
          <img 
            src="https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?auto=format&fit=crop&w=200&h=200" 
            alt="Album cover" 
            className="w-24 h-24 object-cover rounded-lg shadow-sm"
          />
        </div>
      </div>
      <div className="mt-4">
        <div className="font-medium">Alex Playlist</div>
        <button className="text-xs flex items-center text-gray-600 mt-1">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Play on Spotify
        </button>
      </div>
    </div>
  );
};

export default MusicPlaylist;
