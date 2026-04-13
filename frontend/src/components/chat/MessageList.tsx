"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/types/chat";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-subtle">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2Zm1 15h-2v-6h2v6Zm0-8h-2V7h2v2Z"
              fill="var(--color-accent)"
            />
          </svg>
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">
            Wie kann ich helfen?
          </p>
          <p className="mt-1 text-xs text-muted">
            Stelle eine Frage zu deiner Steuererklärung.
          </p>
        </div>
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          {[
            "Homeoffice absetzen",
            "Pendlerpauschale berechnen",
            "Laptop von der Steuer absetzen",
            "Riester-Rente eintragen",
          ].map((suggestion) => (
            <button
              key={suggestion}
              className="rounded-full border border-border bg-surface-raised px-3 py-1.5 text-xs text-muted transition-colors hover:border-accent hover:text-accent"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 px-4 py-6">
      {messages.map((message) =>
        message.role === "user" ? (
          <UserMessage key={message.id} message={message} />
        ) : (
          <AssistantMessage key={message.id} message={message} />
        )
      )}
      <div ref={bottomRef} aria-hidden />
    </div>
  );
}
