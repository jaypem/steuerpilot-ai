"use client";

import { useChatContext } from "@/context/ChatContext";

export default function ErrorToast() {
  const { errorMessage, clearError } = useChatContext();

  if (!errorMessage) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-risk-high bg-surface-raised px-4 py-3 shadow-lg"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
        <path
          d="M8 2a6 6 0 1 0 0 12A6 6 0 0 0 8 2Zm.75 8.5h-1.5v-1.5h1.5v1.5Zm0-3h-1.5V5h1.5v2.5Z"
          fill="var(--color-risk-high)"
        />
      </svg>
      <p className="text-sm text-foreground">{errorMessage}</p>
      <button
        onClick={clearError}
        aria-label="Fehlermeldung schließen"
        className="ml-1 rounded p-0.5 text-muted transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
          <path
            d="M2 2l10 10M12 2 2 12"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </div>
  );
}
