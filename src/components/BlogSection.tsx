import React, { useState } from "react";
import ReactDOM from "react-dom";

const blogs = [
  {
    title:
      "Decoding Blockchain: Understanding the Technology Through Analogies",
    url: "https://learnwithntsh.substack.com/p/decoding-blockchain-understanding",
    image:"https://substackcdn.com/image/fetch/w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F367ddd78-6c06-4cdd-9768-4bd88e7e1193_1200x630.png",
    date: "2023-09-01",
  },
  {
    title: "Why banning cryptos in India is a very bad idea?",
    date: "2023-08-15",
    image:"https://miro.medium.com/v2/resize:fit:720/format:webp/1*y1M1g4OddVhxXVXk4QfAdw.png",
    url: "https://medium.com/@patelnitish/why-banning-cryptos-in-india-is-a-very-bad-idea-5696751ca1ff",
  },
  // Add more posts as needed
];

const BlogSection: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const renderBlogs = (limit: number = blogs.length) => (
    <div className="flex flex-col space-y-4">
      {blogs.slice(0, limit).map((blog, index) => (
        <div key={index} className="flex items-start">
          <img
            src={blog.image}
            alt={blog.title}
            className="w-32 h-20 rounded-lg shadow-sm"
            style={{ objectFit: "cover" }}
          />
          <div className="ml-4">
            <h4 className="font-medium">{blog.title}</h4>
            <p className="text-sm text-gray-500 mt-1">{blog.date}</p>
            <a
              href={blog.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline mt-1"
            >
              Read Blog
            </a>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div>
      <h3 className="text-lg font-medium mb-4">Latest Blog Posts</h3>
      {renderBlogs(2)}
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
        Read all posts
      </button>

      {/* Modal via Portal */}
      {isModalOpen &&
        ReactDOM.createPortal(
          <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-lg w-full max-h-[70vh] overflow-y-auto shadow-lg">
              <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2">
                <h3 className="text-lg font-medium">All Blog Posts</h3>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="text-gray-600 text-2xl font-bold"
                >
                  &times;
                </button>
              </div>
              {renderBlogs()}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
};

export default BlogSection;
