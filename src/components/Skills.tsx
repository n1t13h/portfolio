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
  { name: 'Postgres', className: 'devicon-postgresql-plain' }
];

const Skills: React.FC = () => {
  return (
    <div>
      <h3 className="text-lg font-medium mb-4">Skills</h3>
      {/* Grid layout: 3 columns on default, 4 columns on small screens and up */}
      <div className="grid grid-cols-3 sm:grid-cols-4 gap-6">
        {skills.map((skill) => (
          <div key={skill.name} className="group flex flex-col items-center">
            <i className={`${skill.className} devicon-icon text-2xl`} />
            <span className="mt-2 text-sm">{skill.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Skills;
