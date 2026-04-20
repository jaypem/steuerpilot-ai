"use client";

import { useState, useRef, useEffect } from "react";
import type { Message } from "@/types/chat";
import { exportMarkdown, exportPDF } from "@/lib/exportChat";

interface ExportButtonProps {
  messages: Message[];
  taxYear: number;
}

export default function ExportButton({ messages, taxYear }: ExportButtonProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const exportable = messages.filter((m) => !m.isStreaming);
  if (exportable.length === 0) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Konversation exportieren"
        className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-muted transition-colors hover:bg-border hover:text-foreground"
      >
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden>
          <path
            d="M6.5 1v7M3.5 5l3 3 3-3M1.5 9.5v1a1 1 0 001 1h8a1 1 0 001-1v-1"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        Export
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-36 overflow-hidden rounded-md border border-border bg-surface-raised shadow-lg">
          <button
            onClick={() => { exportMarkdown(exportable, taxYear); setOpen(false); }}
            className="flex w-full items-center gap-2 px-3 py-2 text-xs text-foreground transition-colors hover:bg-border"
          >
            <span className="font-mono text-muted">.md</span>
            Markdown
          </button>
          <button
            onClick={() => { exportPDF(exportable, taxYear); setOpen(false); }}
            className="flex w-full items-center gap-2 px-3 py-2 text-xs text-foreground transition-colors hover:bg-border"
          >
            <span className="font-mono text-muted">.pdf</span>
            PDF
          </button>
        </div>
      )}
    </div>
  );
}
