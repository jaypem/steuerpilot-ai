"use client";

import { useRef, useState } from "react";

const CHAR_WARN_THRESHOLD = 500;
const MAX_CHARS = 2000;

interface ChatInputProps {
  onSubmit: (message: string) => void;
  isLoading?: boolean;
}

export default function ChatInput({ onSubmit, isLoading = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    setValue(el.value);
    // Auto-Resize
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const charsLeft = MAX_CHARS - value.length;
  const showCounter = value.length >= CHAR_WARN_THRESHOLD;

  return (
    <div className="border-t border-border bg-surface-raised px-4 py-3">
      {showCounter && (
        <p
          className={`mb-1 text-right text-xs ${
            charsLeft < 100 ? "text-risk-high" : "text-muted"
          }`}
        >
          {charsLeft} Zeichen übrig
        </p>
      )}
      <div className="flex items-end gap-2 rounded-xl border border-border bg-surface px-3 py-2 focus-within:border-accent focus-within:ring-1 focus-within:ring-accent">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          maxLength={MAX_CHARS}
          rows={1}
          placeholder="Frage zur Steuererklärung stellen… (Enter zum Senden)"
          aria-label="Nachricht eingeben"
          disabled={isLoading}
          className="max-h-[200px] flex-1 resize-none bg-transparent text-sm text-foreground placeholder:text-muted focus:outline-none disabled:opacity-50"
        />
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || isLoading}
          aria-label="Nachricht senden"
          className="mb-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent text-white transition-colors hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <svg
              className="animate-spin"
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="none"
              aria-hidden
            >
              <circle
                cx="7"
                cy="7"
                r="5.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeDasharray="20"
                strokeDashoffset="10"
              />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
              <path
                d="M7 12V2M2 7l5-5 5 5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
      </div>
      <p className="mt-1.5 text-center text-xs text-muted">
        Kein Ersatz für steuerliche Beratung gem. StBerG · Shift+Enter für Zeilenumbruch
      </p>
    </div>
  );
}
