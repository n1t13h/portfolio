import { useEffect, useState } from "preact/hooks";
import "./app.css";
import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import ItemCard from "./components/ItemCard";
import { motion, useAnimation, useScroll, useSpring } from "framer-motion";

import { useInView } from "react-intersection-observer";
import { projects } from "./data/projects";
import { blogs } from "./data/blogs";

export function App() {
  return (
    <div className="container mx-auto">
      <div className="grid grid-cols-2 ">
        <div className="self-start sticky top-0 col-span-1">
          <Hero />
        </div>
        <div class="scrollable-cards">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1 }}
          >
            <h3 className="text-3xl font-bold">Projects</h3>
            {projects.map((project) => {
              return (
                <ItemCard
                  title={project.name}
                  description={project.description}
                  image={project.image}
                  url={project.url}
                  tags={project.tags}
                />
              );
            })}
          </motion.div>
          <div className="col-span-1">
            <h3 className="text-3xl font-bold">Blogs</h3>
            {blogs.map((blog) => {
              return <ItemCard title={blog.title} url={blog.url} />;
            })}
          </div>
        </div>
      </div>
      <div className="footer">
        <p className="text-center text-gray-500">
          Made with 🧡 by Nitish Patel
        </p>
      </div>
    </div>
  );
}
