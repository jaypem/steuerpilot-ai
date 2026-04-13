"use client";

import { useState } from "react";
import type { Source } from "@/types/chat";

interface SourceChipProps {
  source: Source;
}

export default function SourceChip({ source }: SourceChipProps) {
  const [expanded, setExpanded] = useState(false);

  const label = `${source.paragraph} ${source.section} ${source.law}`;

  return (
    <div className="inline-block">
      <button
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        className="inline-flex items-center gap-1 rounded-full border border-accent bg-accent-subtle px-2.5 py-0.5 font-mono text-xs font-medium text-accent transition-colors hover:bg-accent hover:text-white"
      >
        {label}
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="none"
          aria-hidden
          className={`transition-transform duration-150 ${expanded ? "rotate-180" : ""}`}
        >
          <path
            d="M2 3.5 5 6.5 8 3.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {expanded && (
        <div className="mt-1.5 max-w-sm rounded-lg border border-border bg-surface-raised p-3 shadow-sm">
          <p className="mb-1 font-mono text-xs font-semibold text-accent">
            {label}
          </p>
          <p className="text-xs leading-relaxed text-foreground">{source.text}</p>
          {source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1.5 inline-block text-xs text-accent hover:underline"
            >
              Quelle öffnen ↗
            </a>
          )}
        </div>
      )}
    </div>
  );
}
