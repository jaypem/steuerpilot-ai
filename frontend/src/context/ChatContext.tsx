"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import type { Message } from "@/types/chat";
import type { Session } from "@/types/session";
import { useMockChat } from "@/hooks/useMockChat";
import { MOCK_SESSIONS } from "@/lib/mockSessions";

// ─── Initiale Demo-Nachrichten für Session 1 ────────────────────────────────

const INITIAL_MESSAGES: Message[] = [
  {
    id: "init-1",
    role: "user",
    content: "Kann ich mein Homeoffice von der Steuer absetzen?",
    timestamp: new Date(),
  },
  {
    id: "init-2",
    role: "assistant",
    content:
      "Ja, Homeoffice-Kosten können Sie steuerlich geltend machen. Seit 2023 gilt die erhöhte Tagespauschale von 6 € pro Tag (max. 1.260 € im Jahr, also 210 Tage).\n\nAlternativ können Sie ein häusliches Arbeitszimmer absetzen, wenn es ausschließlich beruflich genutzt wird — dann sind die tatsächlichen anteiligen Kosten absetzbar, was bei größeren Wohnungen deutlich mehr einbringen kann.\n\nHaben Sie auch Arbeitsmittel wie Laptop, Monitor oder Bürostuhl gekauft?",
    sources: [
      {
        law: "EStG",
        paragraph: "§ 4",
        section: "Abs. 5 Nr. 6b",
        text: "Für jeden Kalendertag, an dem der Steuerpflichtige seine betriebliche oder berufliche Tätigkeit ausschließlich in der häuslichen Wohnung ausübt, kann er einen Betrag von 6 Euro abziehen, höchstens 1 260 Euro im Wirtschafts- oder Kalenderjahr.",
      },
    ],
    riskBadge: {
      level: "low",
      label: "Unstreitig",
      explanation: "Seit 2023 gesetzlich klar geregelt in § 4 Abs. 5 Nr. 6b EStG.",
    },
    savingAmount: 252,
    timestamp: new Date(),
  },
];

// ─── Typen ───────────────────────────────────────────────────────────────────

export interface SavingEntry {
  label: string;
  amount: number;
  riskLevel: "low" | "medium" | "high";
}

interface ChatContextValue {
  // Chat
  messages: Message[];
  isLoading: boolean;
  submitMessage: (text: string) => void;
  // Sessions
  sessions: Session[];
  activeSessionId: string;
  selectSession: (id: string) => void;
  newSession: () => void;
  // Computed
  totalSaving: number;
  savingEntries: SavingEntry[];
}

// ─── Context ─────────────────────────────────────────────────────────────────

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChatContext() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used inside ChatProvider");
  return ctx;
}

// ─── Provider ────────────────────────────────────────────────────────────────

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>(MOCK_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string>(
    MOCK_SESSIONS[0].id
  );

  const { messages, isLoading, submitMessage } = useMockChat({
    initialMessages: INITIAL_MESSAGES,
  });

  // Gesamt-Ersparnis + Positions-Liste aus aktuellen Nachrichten berechnen
  const savingEntries = useMemo<SavingEntry[]>(() => {
    return messages
      .filter((m) => m.role === "assistant" && m.savingAmount)
      .map((m) => ({
        label: m.content.split("\n")[0].slice(0, 65),
        amount: m.savingAmount!,
        riskLevel: m.riskBadge?.level ?? "low",
      }));
  }, [messages]);

  const totalSaving = useMemo(
    () => savingEntries.reduce((sum, e) => sum + e.amount, 0),
    [savingEntries]
  );

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
    // In Phase 10 werden hier echte Session-Messages geladen
  }, []);

  const newSession = useCallback(() => {
    const id = `session-${Date.now()}`;
    const newSess: Session = {
      id,
      title: "Neue Konversation",
      createdAt: new Date(),
      messageCount: 0,
    };
    setSessions((prev) => [newSess, ...prev]);
    setActiveSessionId(id);
  }, []);

  // Aktive Session messageCount + totalSaving aktuell halten
  useMemo(() => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? { ...s, messageCount: messages.length, totalSaving }
          : s
      )
    );
  }, [messages.length, totalSaving, activeSessionId]);

  return (
    <ChatContext.Provider
      value={{
        messages,
        isLoading,
        submitMessage,
        sessions,
        activeSessionId,
        selectSession,
        newSession,
        totalSaving,
        savingEntries,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}
