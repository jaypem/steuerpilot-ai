import { useState, useCallback, RefObject } from 'react';

interface DropdownPosition {
  openUpward: boolean;
  maxHeight: number;
}

export function useDropdownPosition(
  ref: RefObject<HTMLElement | null>,
  maxHeight: number,
  gap: number = 4
): { position: DropdownPosition; recalculate: () => void } {
  const [position, setPosition] = useState<DropdownPosition>({
    openUpward: false,
    maxHeight,
  });

  const recalculate = useCallback(() => {
    if (!ref.current) return;

    const rect = ref.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const spaceAbove = rect.top - gap;
    const openUpward = spaceBelow < maxHeight && spaceAbove > spaceBelow;
    const available = openUpward ? spaceAbove : spaceBelow;

    setPosition({ openUpward, maxHeight: Math.min(maxHeight, available) });
  }, [ref, maxHeight, gap]);

  return { position, recalculate };
}
