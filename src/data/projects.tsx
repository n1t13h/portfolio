type Project = {
  name: string;
  description: string;
  image: string;
  url?: string;
  tags: string[];
};

export const projects: Project[] = [
  {
    name: "Document Attestation",
    description:
      "A blockchain based document attestation system built using Open Attestation",
    image: "preact-portfolio.png",
    tags: ["Blockchain", "Open Attestation", "Account Abstraction"],
  },
  {
    name: "Staking Pool",
    description: "A staking pool built for an EVN compatible blockchain",
    image: "preact-portfolio.png",
    tags: ["Web3", "Ethereum", "Solidity", "React", "Django"],
  },
  {
    name: "Asset Tokenization",
    description:
      "A blockchain based asset tokenization system built on EVM compatible blockchains",
    image: "preact-portfolio.png",
    tags: ["Web3", "Ethereum", "Solidity", "React", "Django"],
  },
  {
    name: "Blockchain Identity Management",
    description:
      "A blockchain based identity management system built on Hyperledger Fabric",
    image: "preact-portfolio.png",
    url: "https://github.com/nitishpatel/blockchain-identity-management-system",
    tags: [
      "Blockchain",
      "Hyperledger",
      "Fabric",
      "React",
      "NodeJS",
      "Express",
      "MongoDB",
    ],
  },
  {
    name: "TabTrail",
    description: "A chrome extension to manage your tab groups",
    image: "tabtrail.png",
    url: "https://github.com/nitishpatel/tabtrail",
    tags: ["Chrome Extension", "React"],
  },
  {
    name: "Turf Booking System",
    description: "A turf booking system built on React-DRF stack",
    image: "turf.png",
    url: "https://github.com/nitishpatel/turf",
    tags: ["React", "Django", "DRF", "PostgreSQL"],
  },
  {
    name: "Troupe",
    description: "A social media platform for sharing a collection of links",
    image: "troupe.png",
    url: "https://github.com/nitishpatel/troupe",
    tags: ["Flutter", "Firebase", "Dart"],
  },
];
