import { useState, useCallback, useEffect, RefObject } from 'react';

interface DropdownOptions {
  maxHeight: number;
  minWidth?: number;
  maxWidth?: number;
}

interface DropdownPosition {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
}

interface UseDropdownResult {
  isOpen: boolean;
  toggle: () => void;
  close: () => void;
  position: DropdownPosition | null;
}

export function useDropdown(
  triggerRef: RefObject<HTMLElement | null>,
  dropdownRef: RefObject<HTMLElement | null>,
  options: DropdownOptions
): UseDropdownResult {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<DropdownPosition | null>(null);

  const calculatePosition = useCallback(() => {
    if (!triggerRef.current) return;

    const rect = triggerRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom - 4;
    const spaceAbove = rect.top - 4;
    const openUpward = spaceBelow < options.maxHeight && spaceAbove > spaceBelow;
    const available = openUpward ? spaceAbove : spaceBelow;
    const maxH = Math.min(options.maxHeight, available);

    let width = rect.width;
    if (options.minWidth) width = Math.max(width, options.minWidth);
    if (options.maxWidth) width = Math.min(width, options.maxWidth);

    let left = rect.left;
    const vw = window.innerWidth;
    if (left + width > vw - 8) left = vw - width - 8;
    if (left < 8) left = 8;

    const top = openUpward ? rect.top - maxH - 4 : rect.bottom + 4;

    setPosition({ top: Math.max(8, top), left, width, maxHeight: maxH });
  }, [triggerRef, options.maxHeight, options.minWidth, options.maxWidth]);

  const toggle = useCallback(() => {
    if (!isOpen) calculatePosition();
    setIsOpen(prev => !prev);
  }, [isOpen, calculatePosition]);

  const close = useCallback(() => setIsOpen(false), []);

  useEffect(() => {
    if (!isOpen) return;

    const handleMouseDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        !triggerRef.current?.contains(target) &&
        !dropdownRef.current?.contains(target)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, [isOpen, triggerRef, dropdownRef]);

  return { isOpen, toggle, close, position };
}
