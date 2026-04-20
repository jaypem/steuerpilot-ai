"use client";

import { useRef, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown } from 'lucide-react';
import { useDropdown } from '@/hooks/useDropdown';

interface ModernSelectOption {
  value: string | number;
  label: string;
  preset_type?: 'date_range' | 'filter' | 'combined';
}

interface ModernSelectProps {
  value: string | number;
  onChange: (value: string | number) => void;
  options: ModernSelectOption[];
  placeholder?: string;
  disabled?: boolean;
}

export const ModernSelect: React.FC<ModernSelectProps> = ({
  value,
  onChange,
  options,
  placeholder = 'Auswählen…',
  disabled = false,
}) => {
  const triggerRef  = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const maxDropdownHeight = Math.min(300, options.length * 36 + 8);
  const { isOpen, toggle, close, position } = useDropdown(triggerRef, dropdownRef, { maxHeight: maxDropdownHeight });

  const selectedOption = options.find(opt => opt.value === value);
  const hasPresetTypes = useMemo(() => options.some(opt => opt.preset_type), [options]);

  const handleSelect = (v: string | number) => { onChange(v); close(); };

  const renderOption = (option: ModernSelectOption) => (
    <div
      key={option.value}
      onClick={() => handleSelect(option.value)}
      className={`px-3 py-2 text-sm cursor-pointer font-medium transition-all ${
        option.value === value
          ? 'bg-accent-subtle text-accent border-l-4 border-accent'
          : 'hover:bg-border text-foreground'
      }`}
    >
      {option.label}
    </div>
  );

  const renderGrouped = () => {
    const dateRange = options.filter(o => o.preset_type === 'date_range' || o.preset_type === 'combined');
    const filter    = options.filter(o => o.preset_type === 'filter'     || o.preset_type === 'combined');
    return (
      <>
        {dateRange.length > 0 && (
          <>
            <div className="px-3 py-1.5 text-xs font-semibold text-muted bg-surface border-b border-border">Zeitraum</div>
            {dateRange.map(renderOption)}
          </>
        )}
        {filter.length > 0 && (
          <>
            {dateRange.length > 0 && <div className="border-t border-border my-1" />}
            <div className="px-3 py-1.5 text-xs font-semibold text-muted bg-surface border-b border-border">Filter</div>
            {filter.map(renderOption)}
          </>
        )}
      </>
    );
  };

  return (
    <div ref={triggerRef} className="relative">
      <div
        onClick={() => !disabled && toggle()}
        className={`w-full flex items-center justify-between px-3 py-2 text-sm border-2 rounded-lg transition-all ${
          disabled
            ? 'border-border bg-surface text-muted cursor-not-allowed'
            : 'border-border bg-surface-raised text-foreground hover:border-accent focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent cursor-pointer'
        }`}
      >
        <span className={selectedOption ? 'text-foreground font-medium' : 'text-muted'}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown className={`w-4 h-4 text-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </div>

      {isOpen && position && createPortal(
        <div
          ref={dropdownRef}
          onClick={e => e.stopPropagation()}
          className="fixed bg-surface-raised border-2 border-accent/30 rounded-lg shadow-2xl z-[99999] overflow-y-auto"
          style={{
            top:       `${position.top}px`,
            left:      `${position.left}px`,
            width:     `${position.width}px`,
            maxHeight: `${position.maxHeight}px`,
          }}
        >
          {hasPresetTypes ? renderGrouped() : options.map(renderOption)}
        </div>,
        document.body
      )}
    </div>
  );
};
