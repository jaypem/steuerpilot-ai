"use client";

import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, ChevronDown, Check, Search, Loader2 } from 'lucide-react';
import { useDropdown } from '@/hooks/useDropdown';

interface ModernMultiSelectProps {
  options: string[];
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  loading?: boolean;
  onEnter?: (value?: string[]) => void;
  isTruncated?: boolean;
  onServerSearch?: (searchTerm: string) => void;
  serverSearchResults?: string[] | null;
  isServerSearching?: boolean;
}

export const ModernMultiSelect: React.FC<ModernMultiSelectProps> = ({
  options,
  value,
  onChange,
  placeholder,
  loading = false,
  onEnter,
  isTruncated = false,
  onServerSearch,
  serverSearchResults,
  isServerSearching = false,
}) => {
  const defaultPlaceholder = placeholder ?? 'Auswählen…';

  const [searchTerm, setSearchTerm] = useState('');
  const [pendingValue, setPendingValue] = useState<string[]>(value);
  const containerRef    = useRef<HTMLDivElement>(null);
  const dropdownRef     = useRef<HTMLDivElement>(null);
  const debounceRef     = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 480;
  const { isOpen, toggle, close, position } = useDropdown(containerRef, dropdownRef, {
    maxHeight: 350,
    minWidth: 220,
    maxWidth: isMobile ? window.innerWidth - 16 : 320,
  });

  useEffect(() => {
    if (isOpen) setPendingValue(value);
  }, [isOpen, value]);

  const handleSearchChange = (term: string) => {
    setSearchTerm(term);
    if (isTruncated && onServerSearch) {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => onServerSearch(term), 300);
    }
  };

  const clientFiltered = options.filter(opt =>
    !searchTerm || opt.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredOptions = (() => {
    if (!isTruncated || !serverSearchResults || !searchTerm) return clientFiltered;
    const clientSet = new Set(clientFiltered);
    const merged = [...clientFiltered];
    for (const v of serverSearchResults) {
      if (!clientSet.has(v)) merged.push(v);
    }
    return merged;
  })();

  const toggleOption = (option: string) =>
    setPendingValue(prev =>
      prev.includes(option) ? prev.filter(v => v !== option) : [...prev, option]
    );

  const handleApply = () => {
    close();
    setSearchTerm('');
    onEnter ? onEnter(pendingValue) : onChange(pendingValue);
  };

  const handleCancel = () => {
    setPendingValue(value);
    close();
    setSearchTerm('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredOptions.length > 0 && searchTerm) {
        const exact = filteredOptions.find(o => o.toLowerCase() === searchTerm.toLowerCase());
        toggleOption(exact ?? filteredOptions[0]);
        setSearchTerm('');
      } else {
        handleApply();
      }
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  const removeValue = (v: string) => {
    const next = value.filter(x => x !== v);
    onChange(next);
    onEnter?.(next);
  };

  const isAllSelected = filteredOptions.length > 0 && filteredOptions.every(o => pendingValue.includes(o));
  const hasChanges = pendingValue.length !== value.length ||
    [...pendingValue].sort().some((v, i) => v !== [...value].sort()[i]);

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger */}
      <div
        onClick={() => !loading && toggle()}
        className={`min-h-[32px] px-2 py-1 text-xs border border-border rounded bg-surface-raised text-foreground flex items-center justify-between ${loading ? 'cursor-wait opacity-75' : 'cursor-pointer'}`}
      >
        <div className="flex-1 flex flex-wrap gap-1">
          {loading ? (
            <span className="flex items-center gap-2 text-muted">
              <Loader2 className="w-3 h-3 animate-spin" />
              Lädt…
            </span>
          ) : value.length === 0 ? (
            <span className="text-muted">{defaultPlaceholder}</span>
          ) : (
            value.map(val => (
              <span key={val} className="inline-flex items-center gap-1 px-2 py-0.5 bg-accent-subtle text-accent rounded text-xs">
                <span className="truncate max-w-[80px]">{val}</span>
                <button onClick={e => { e.stopPropagation(); removeValue(val); }} className="hover:bg-accent/20 rounded-full p-0.5">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))
          )}
        </div>
        {loading
          ? <Loader2 className="w-4 h-4 text-accent animate-spin" />
          : <ChevronDown className={`w-4 h-4 text-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        }
      </div>

      {/* Dropdown */}
      {isOpen && position && createPortal(
        <div
          ref={dropdownRef}
          onClick={e => e.stopPropagation()}
          className="fixed bg-surface-raised border border-border rounded-lg shadow-xl z-[99999] max-h-[350px] flex flex-col"
          style={{ top: position.top, left: position.left, width: position.width }}
        >
          {/* Search + controls */}
          <div className="p-2 border-b border-border space-y-2">
            <div className="relative">
              {isServerSearching
                ? <Loader2 className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-accent animate-spin" />
                : <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted" />
              }
              <input
                type="text"
                placeholder={isTruncated ? 'Alle Werte durchsuchen…' : 'Suchen…'}
                value={searchTerm}
                onChange={e => handleSearchChange(e.target.value)}
                onKeyDown={handleKeyDown}
                onClick={e => e.stopPropagation()}
                autoFocus
                className="w-full pl-7 pr-3 py-1.5 text-xs bg-surface-raised border-0 border-b border-border rounded-none focus:outline-none focus:border-muted text-foreground placeholder-muted transition-colors"
              />
            </div>
            {filteredOptions.length > 0 && (
              <div className="flex gap-1">
                <button type="button" onClick={() => setPendingValue(filteredOptions)} disabled={isAllSelected}
                  className="flex-1 text-xs px-2 py-1 text-accent hover:bg-accent-subtle rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                  Alle wählen
                </button>
                <button type="button" onClick={() => setPendingValue([])} disabled={pendingValue.length === 0}
                  className="flex-1 text-xs px-2 py-1 text-muted hover:bg-border rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                  Leeren
                </button>
              </div>
            )}
          </div>

          {/* Options */}
          <div className="flex-1 overflow-y-auto" onWheel={e => e.stopPropagation()}>
            {loading ? (
              <div className="p-3 text-center text-xs text-muted">Lädt…</div>
            ) : filteredOptions.length === 0 ? (
              <div className="p-3 text-center text-xs text-muted">
                {isServerSearching ? 'Suche läuft…' : searchTerm ? 'Keine Treffer' : 'Keine Optionen'}
              </div>
            ) : filteredOptions.map(option => {
              const isSelected = pendingValue.includes(option);
              return (
                <div key={option} onClick={() => toggleOption(option)}
                  className={`flex items-center gap-2 px-3 py-2 text-xs cursor-pointer hover:bg-border transition-colors ${isSelected ? 'bg-accent-subtle' : ''}`}
                >
                  <div className={`w-4 h-4 border rounded flex items-center justify-center flex-shrink-0 transition-colors ${
                    isSelected ? 'bg-accent border-accent text-white' : 'border-border'
                  }`}>
                    {isSelected && <Check className="w-3 h-3" />}
                  </div>
                  <span className="flex-1 truncate text-foreground">{option}</span>
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="p-2 border-t border-border flex gap-2">
            <button type="button" onClick={handleCancel}
              className="flex-1 px-3 py-1.5 text-xs font-medium text-foreground bg-border hover:bg-border rounded transition-colors">
              Abbrechen
            </button>
            <button type="button" onClick={handleApply} disabled={!hasChanges}
              className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-accent hover:bg-accent-hover rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              Übernehmen {pendingValue.length > 0 && `(${pendingValue.length})`}
            </button>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};
