import React from 'react';

// List of skills with the Devicons class names
const skills = [
  { name: 'AWS', className: 'devicon-amazonwebservices-line-wordmark' },
  { name: 'JavaScript', className: 'devicon-javascript-plain' },
  { name: 'Python', className: 'devicon-python-plain' },
  { name: 'TypeScript', className: 'devicon-typescript-plain' },
  { name: 'Bash', className: 'devicon-bash-plain' },
  { name: 'Solidity', className: 'devicon-solidity-plain' },
  { name: 'Flask', className: 'devicon-flask-original' },
  { name: 'Django', className: 'devicon-django-plain' },
  { name: 'Django REST', className: 'devicon-djangorest-plain' }, // Using same icon as Django
  { name: 'Prisma', className: 'devicon-nodejs-plain' }, // No official Prisma icon in Devicons; using a substitute
  { name: 'Redis', className: 'devicon-redis-plain' },
  { name: 'MongoDB', className: 'devicon-mongodb-plain' },
  { name: 'MySQL', className: 'devicon-mysql-plain' },
  { name: 'Postgres', className: 'devicon-postgresql-plain' },
  // AI Stack
  { name: 'PyTorch', className: 'devicon-pytorch-original' },
  { name: 'TensorFlow', className: 'devicon-tensorflow-original' },
  { name: 'LangChain', className: 'devicon-python-plain' }, // Python ecosystem
  { name: 'OpenAI', className: 'devicon-network-plain' }, // Conceptual icon
  { name: 'Hugging Face', className: 'devicon-python-plain' } // Python ecosystem
];

const Skills: React.FC = () => {
  return (
    <div className="flex flex-wrap gap-2">
      {skills.map((skill) => (
        <div
          key={skill.name}
          className="group flex items-center gap-2 px-3 py-1.5 border border-border hover:bg-foreground hover:text-background hover:border-foreground transition-all duration-300 cursor-default"
        >
          <i className={`${skill.className} text-lg text-muted-foreground group-hover:text-background transition-colors`} />
          <span className="text-sm font-mono text-muted-foreground group-hover:text-background transition-colors uppercase">{skill.name}</span>
        </div>
      ))}
    </div>
  );
};

export default Skills;
