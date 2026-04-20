"use client";

import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown } from 'lucide-react';
import { useClickOutside } from '@/hooks/useClickOutside';
import { useDropdownPosition } from '@/hooks/useDropdownPosition';

interface Option {
  value: string;
  label: string;
}

interface ModernDropdownProps {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  placeholder?: string;
  compact?: boolean;
}

export const ModernDropdown: React.FC<ModernDropdownProps> = ({
  value,
  onChange,
  options,
  placeholder = 'Auswählen…',
  compact = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState<{
    top: number; left: number; width: number; maxHeight: number;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef  = useRef<HTMLDivElement>(null);

  const selectedOption = options.find(opt => opt.value === value);

  const itemHeight = 44;
  const idealHeight = options.length * itemHeight + 8;
  const maxDropdownHeight = Math.min(320, idealHeight);

  const { position: verticalPos, recalculate } = useDropdownPosition(containerRef, maxDropdownHeight, 8);

  useClickOutside([containerRef, dropdownRef], () => setIsOpen(false), isOpen);

  useEffect(() => {
    if (isOpen) recalculate();
  }, [isOpen, options.length, recalculate]);

  useEffect(() => {
    if (!isOpen || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const vw = window.innerWidth;
    const top = verticalPos.openUpward
      ? rect.top - verticalPos.maxHeight - 4
      : rect.bottom + 4;
    let left = rect.left;
    if (left + rect.width > vw - 8) left = vw - rect.width - 8;
    if (left < 8) left = 8;
    setDropdownPosition({ top: Math.max(8, top), left, width: rect.width, maxHeight: verticalPos.maxHeight });
  }, [isOpen, verticalPos]);

  const triggerClass = compact
    ? 'flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors bg-border text-muted hover:bg-border'
    : 'w-full flex items-center justify-between px-3 py-2 text-sm border-2 border-border rounded-lg bg-surface-raised text-foreground hover:border-accent focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-all';

  return (
    <div ref={containerRef} className="relative">
      <button onClick={() => setIsOpen(!isOpen)} className={triggerClass}>
        <span className={compact ? 'text-muted' : (selectedOption ? 'text-foreground font-medium' : 'text-muted')}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown className={`${compact ? 'w-3 h-3' : 'w-4 h-4'} text-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && dropdownPosition && createPortal(
        <div
          ref={dropdownRef}
          onClick={e => e.stopPropagation()}
          className="fixed bg-surface-raised border-2 border-accent/30 rounded-lg shadow-2xl z-[99999] overflow-y-auto"
          style={{
            top:       `${dropdownPosition.top}px`,
            left:      `${dropdownPosition.left}px`,
            width:     `${dropdownPosition.width}px`,
            maxHeight: `${dropdownPosition.maxHeight}px`,
          }}
        >
          {options.map(option => (
            <button
              key={option.value}
              onClick={() => { onChange(option.value); setIsOpen(false); }}
              className={`w-full text-left px-3 py-2 text-sm font-medium transition-all ${
                option.value === value
                  ? 'bg-accent-subtle text-accent border-l-4 border-accent'
                  : 'hover:bg-border text-foreground'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>,
        document.body
      )}
    </div>
  );
};
