
import React from 'react';

const Reading: React.FC = () => {
  return (
    <div>
      <h3 className="text-lg font-medium mb-4">What I'm reading</h3>
      <div className="flex items-start">
        <img 
          src="https://images.unsplash.com/photo-1589998059171-988d887df646?auto=format&fit=crop&w=150&h=200" 
          alt="Book cover" 
          className="w-28 h-36 object-cover rounded-md shadow-sm"
        />
        <div className="ml-4">
          <h4 className="font-medium">Dieter Rams the Complete Works</h4>
          <p className="text-sm text-gray-500">Klaus Klemp</p>
        </div>
      </div>
    </div>
  );
};

export default Reading;
