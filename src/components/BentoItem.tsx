
import React from 'react';
import { cn } from '@/lib/utils';

interface BentoItemProps {
  children: React.ReactNode;
  className?: string;
  colSpan?: number;
  rowSpan?: number;
}

const BentoItem: React.FC<BentoItemProps> = ({
  children,
  className = '',
  colSpan = 1,
  rowSpan = 1
}) => {
  const colSpanClass = colSpan === 2 ? 'md:col-span-2' : colSpan === 3 ? 'md:col-span-3' : '';

  const rowSpanClass = rowSpan === 2 ? 'md:row-span-2' : '';

  return (
    <div
      className={cn(
        'bento-card animate-slideUp opacity-0',
        colSpanClass,
        rowSpanClass,
        className
      )}
      style={{
        animationDelay: `${Math.random() * 0.5}s`
      }}
    >
      {children}
    </div>
  );
};

export default BentoItem;
