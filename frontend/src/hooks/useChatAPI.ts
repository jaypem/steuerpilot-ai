"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Message, RiskBadge, Source } from "@/types/chat";
import { streamChat } from "@/lib/api";

interface UseChatAPIOptions {
  sessionId?: string;
  taxYear?: number;
  onDone?: () => void;
}

export function useChatAPI({ sessionId, taxYear, onDone }: UseChatAPIOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Replace the entire message list (used when switching sessions)
  const resetMessages = useCallback((next: Message[] = []) => {
    setMessages(next);
  }, []);

  const submitMessage = useCallback(
    async (text: string) => {
      if (isLoading) return;

      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setErrorMessage(null);

      const assistantId = `assistant-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          isStreaming: true,
          timestamp: new Date(),
        },
      ]);

      // Accumulate metadata chunks that arrive after the text stream
      const sources: Source[] = [];
      let riskBadge: RiskBadge | undefined;
      let savingAmount: number | undefined;

      try {
        abortRef.current = new AbortController();

        for await (const chunk of streamChat(
          { message: text, session_id: sessionId, tax_year: taxYear },
          abortRef.current.signal,
        )) {
          switch (chunk.type) {
            case "status":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, statusLabel: chunk.label } : m,
                ),
              );
              break;

            case "text":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, statusLabel: undefined, content: m.content + chunk.content }
                    : m,
                ),
              );
              break;

            case "source":
              sources.push({
                law: chunk.law,
                paragraph: chunk.paragraph,
                section: chunk.section,
                text: chunk.text,
                url: chunk.url ?? undefined,
              });
              break;

            case "risk_badge":
              riskBadge = {
                level: chunk.level,
                label: chunk.label,
                explanation: chunk.explanation,
              };
              break;

            case "saving":
              savingAmount = chunk.amount;
              break;

            case "done":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        isStreaming: false,
                        sources: sources.length > 0 ? sources : undefined,
                        riskBadge,
                        savingAmount,
                      }
                    : m,
                ),
              );
              setIsLoading(false);
              onDone?.();
              break;

            case "error":
              throw new Error(chunk.message);
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        const msg =
          err instanceof Error ? err.message : "Unbekannter Fehler";
        setErrorMessage(msg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, isStreaming: false } : m,
          ),
        );
        setIsLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isLoading, sessionId, taxYear],
  );

  return { messages, isLoading, submitMessage, errorMessage, resetMessages };
}
