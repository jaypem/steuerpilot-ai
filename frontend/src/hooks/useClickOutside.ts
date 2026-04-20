import { useEffect, RefObject } from 'react';

export function useClickOutside(
  refs: RefObject<HTMLElement | null>[],
  callback: () => void,
  enabled: boolean = true
): void {
  useEffect(() => {
    if (!enabled) return;

    const handleMouseDown = (event: MouseEvent) => {
      const target = event.target as Node;
      const isOutside = refs.every(ref => !ref.current?.contains(target));
      if (isOutside) callback();
    };

    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, [refs, callback, enabled]);
}
