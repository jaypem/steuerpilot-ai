"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Message } from "@/types/chat";
import { findMatchingEntry } from "@/lib/mockData";

const WORD_INTERVAL_MS = 35; // Millisekunden pro Wort

interface UseMockChatOptions {
  initialMessages?: Message[];
}

export function useMockChat(options: UseMockChatOptions = {}) {
  const [messages, setMessages] = useState<Message[]>(
    options.initialMessages ?? []
  );
  const [isLoading, setIsLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Interval bei Unmount aufräumen
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const submitMessage = useCallback((text: string) => {
    if (isLoading) return;

    // 1. User-Message hinzufügen
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // 2. Passende Mock-Antwort finden
    const entry = findMatchingEntry(text);
    const words = entry.answer.text.split(" ");
    const assistantId = `assistant-${Date.now()}`;

    // 3. Leere Streaming-Message einfügen
    const streamingMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      isStreaming: true,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, streamingMessage]);

    // 4. Wort für Wort streamen
    let wordIndex = 0;
    intervalRef.current = setInterval(() => {
      wordIndex++;
      const partial = words.slice(0, wordIndex).join(" ");

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: partial } : m
        )
      );

      if (wordIndex >= words.length) {
        clearInterval(intervalRef.current!);
        intervalRef.current = null;

        // 5. Stream abschließen: Sources, Badge, Ersparnis anhängen
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: partial,
                  isStreaming: false,
                  sources: entry.answer.sources,
                  riskBadge: entry.answer.riskBadge,
                  savingAmount: entry.answer.savingAmount,
                }
              : m
          )
        );
        setIsLoading(false);
      }
    }, WORD_INTERVAL_MS);
  }, [isLoading]);

  return { messages, isLoading, submitMessage };
}
