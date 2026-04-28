"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  DOUBLE_TAX_SAVINGS_LABEL,
  DOUBLE_TAX_SAVINGS_TOOLTIP,
} from "@/lib/doubleTaxSavings";
import type { Message } from "@/types/chat";
import { useChatContext } from "@/context/ChatContext";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";

const SUGGESTIONS = [
  "Homeoffice absetzen",
  "Pendlerpauschale berechnen",
  "Laptop von der Steuer absetzen",
  "Riester-Rente eintragen",
];

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  const router = useRouter();
  const {
    submitMessage,
    ideaTransferOnboarding,
    answerIdeaTransferOnboarding,
  } = useChatContext();
  const bottomRef = useRef<HTMLDivElement>(null);
  const visibleMessages =
    messages.length === 0 && ideaTransferOnboarding
      ? ideaTransferOnboarding.transcript
      : messages;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleMessages]);

  if (messages.length === 0 && ideaTransferOnboarding) {
    return (
      <div className="flex h-full flex-col px-4 py-6">
        <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4">
          {ideaTransferOnboarding.transcript.map((message) =>
            message.role === "user" ? (
              <UserMessage key={message.id} message={message} />
            ) : (
              <AssistantMessage key={message.id} message={message} />
            ),
          )}

          {ideaTransferOnboarding.quickReplies.length > 0 && (
            <div className="flex flex-wrap gap-2 px-1">
              {ideaTransferOnboarding.quickReplies.map((reply) => (
                <button
                  key={reply.id}
                  onClick={() => answerIdeaTransferOnboarding(reply.id)}
                  className="rounded-full border border-border bg-surface-raised px-3 py-1.5 text-xs text-muted transition-colors hover:border-accent hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  {reply.label}
                </button>
              ))}
            </div>
          )}

          {ideaTransferOnboarding.ctaHref && (
            <div className="px-1">
              <button
                onClick={() => router.push(ideaTransferOnboarding.ctaHref!)}
                title={DOUBLE_TAX_SAVINGS_TOOLTIP}
                className="inline-flex items-center gap-2 rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover"
              >
                {ideaTransferOnboarding.ctaLabel ??
                  `Zum ${DOUBLE_TAX_SAVINGS_LABEL}-Check`}
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="none"
                  aria-hidden
                >
                  <path
                    d="M4 2l4 4-4 4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
          )}
        </div>
        <div ref={bottomRef} aria-hidden />
      </div>
    );
  }

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
        <div
          className="mt-2 flex flex-wrap justify-center gap-2"
          role="group"
          aria-label="Beispielfragen"
        >
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => submitMessage(suggestion)}
              className="rounded-full border border-border bg-surface-raised px-3 py-1.5 text-xs text-muted transition-colors hover:border-accent hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
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
      {visibleMessages.map((message) =>
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
