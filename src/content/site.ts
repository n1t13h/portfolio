export type ProjectVisual = "rag" | "stake" | "cert";

export const site = {
  links: {
    github: "https://github.com/nitishpatel/",
    linkedin: "https://linkedin.com/in/ntshptl/",
    email: "contact@ntshptl.in",
    resume: "https://drive.google.com/file/d/1lJnzel5i3I2sT_K-zKzNwnAngtSkR-f4/view?usp=sharing",
    unsplash: "https://unsplash.com/@ntshptl",
    instagram: "https://instagram.com/ntshptl",
    calendly: "https://calendly.com/nitishp74/30min",
  },
  hero: {
    headline: "I write software that's still easy to change a year later.",
    sub: "Software craftsperson at Incubyte. Previously team lead at Yodaplus.",
    status: "Open to interesting work.",
  },
  projects: [
    {
      id: "agentic-rag",
      title: "Agentic RAG",
      description: "Autonomous reasoning engine",
      stack: ["AI", "Vector DB"],
      visual: "rag",
    },
    {
      id: "liquid-staking",
      title: "Liquid Staking",
      description: "DeFi protocol for asset staking",
      stack: ["ETH", "Solidity"],
      visual: "stake",
    },
    {
      id: "doc-attestation",
      title: "Doc Attestation",
      description: "Decentralized document verification",
      stack: ["Blockchain", "Next.js"],
      visual: "cert",
    },
  ] as { id: string; title: string; description: string; stack: string[]; visual: ProjectVisual }[],
  thrive: {
    kicker: "Where I thrive",
    paragraph:
      "Five years building products across AI, Web3 and insurance. I like the unglamorous middle of software: clear boundaries, fast tests and code the next person is glad to inherit. I've shipped as an engineer and led the team that ships.",
    capabilities: [
      { title: "Craft & quality", line: "Test-driven development, refactoring, clean architecture, pairing." },
      { title: "AI & data", line: "Agentic RAG, vector search, PyTorch, Python, Django, Flask." },
      { title: "Web3 & cloud", line: "Solidity, TypeScript, AWS serverless, Postgres, Redis." },
    ],
  },
  experience: [
    { company: "Incubyte", role: "Software Craftsperson", years: "2025 — now" },
    { company: "Yodaplus", role: "Team Lead", years: "2023 — 2025" },
    { company: "Yodaplus", role: "Software Engineer", years: "2021 — 2023" },
  ],
  contact: {
    heading: "Got a hard problem worth solving well?",
    line: "Looking for teams that care about craft as much as shipping.",
    cta: "Book a call →",
  },
  photos: {
    camera: "Sony ZV-E10",
    intro:
      "I shoot on a Sony ZV-E10, mostly around Mumbai and on trips through India. Each collection is a short sequence, best seen in order.",
  },
};
