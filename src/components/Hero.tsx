import { useState } from "preact/hooks";
import preactLogo from "../assets/final.png";
import { motion, useAnimation, useScroll, useSpring } from "framer-motion";
import { FaSquareXTwitter } from "react-icons/fa6";
import { FaGithubSquare } from "react-icons/fa";
import { FaLinkedin } from "react-icons/fa";

const startDate = new Date("2021-07-01T00:00:00");
const currentDate = new Date();
const diff = currentDate.getTime() - startDate.getTime();
const years = Math.round(diff / (1000 * 60 * 60 * 24 * 365));

const Hero = () => {
  const variants = {
    hidden: { opacity: 0, y: -20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      className="hero-main"
      initial="hidden"
      animate="visible"
      variants={variants}
      transition={{ duration: 0.6 }}
    >
      <motion.img
        src={preactLogo}
        className="hero-logo"
        alt="Preact Logo"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      />
      <motion.h1
        className="text-6xl font-bold hero-name"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        NITISH PATEL
      </motion.h1>
      <motion.h2
        className="text-3xl hero-title"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.6 }}
      >
        Full Stack Developer
      </motion.h2>
      <motion.p
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1 }}
      >
        <p className="text-xl hero-description">
          Hey there! I'm a seasoned Full Stack Developer with {years} years of
          coding mojo. Dive into my portfolio site and witness the magic of
          Web3, where Full Stack development unfolds seamlessly. From crafting
          sleek interfaces to optimizing powerful backends, my journey is a
          testament to innovation and functionality.
        </p>
      </motion.p>

      {/* Social Links */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1.2 }}
      >
        <div className="social-links">
          <a
            href="
          https://twitter.com/ntshptl"
            target="_blank"
            rel="noopener noreferrer"
          >
            <FaSquareXTwitter className="social-link" />
          </a>
          <a
            href="
          https://github.com/nitishpatel"
            target="_blank"
            rel="noopener noreferrer"
          >
            <FaGithubSquare className="social-link" />
          </a>
          <a
            href="
          https://in.linkedin.com/in/ntshptl"
            target="_blank"
            rel="noopener noreferrer"
          >
            <FaLinkedin className="social-link" />
          </a>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default Hero;
