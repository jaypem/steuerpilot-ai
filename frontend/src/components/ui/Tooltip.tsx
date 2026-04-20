"use client";

import React, { useState } from 'react';

interface TooltipProps {
  content: string | React.ReactNode | null | undefined;
  children: React.ReactNode;
  className?: string;
  side?: 'top' | 'bottom' | 'left' | 'right';
  disabled?: boolean;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  className = '',
  side = 'top',
  disabled = false,
}) => {
  const [isVisible, setIsVisible] = useState(false);

  if (!content || disabled) return <>{children}</>;

  const sideClasses = {
    top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left:   'right-full top-1/2 -translate-y-1/2 mr-2',
    right:  'left-full top-1/2 -translate-y-1/2 ml-2',
  }[side];

  const arrowClasses = {
    top:    'top-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-surface-raised border-l-4 border-r-4 border-t-4',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-surface-raised border-l-4 border-r-4 border-b-4',
    left:   'left-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-surface-raised border-t-4 border-b-4 border-l-4',
    right:  'right-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-surface-raised border-t-4 border-b-4 border-r-4',
  }[side];

  return (
    <div className={`relative inline-block ${className}`}>
      <div onMouseEnter={() => setIsVisible(true)} onMouseLeave={() => setIsVisible(false)}>
        {children}
      </div>
      {isVisible && (
        <div className={`absolute z-40 ${sideClasses}`}>
          <div className="bg-surface-raised border border-border text-foreground text-xs rounded-lg p-3 shadow-xl max-w-sm whitespace-normal break-words">
            {content}
            <div className={`absolute ${arrowClasses}`} />
          </div>
        </div>
      )}
    </div>
  );
};
