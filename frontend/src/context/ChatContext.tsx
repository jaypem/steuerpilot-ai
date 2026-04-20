"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { Message } from "@/types/chat";
import type { Session } from "@/types/session";
import { useMockChat } from "@/hooks/useMockChat";
import { useChatAPI } from "@/hooks/useChatAPI";
import { MOCK_SESSIONS } from "@/lib/mockSessions";
import {
  deleteSession as apiDeleteSession,
  fetchSessionMessages,
  fetchSessions,
} from "@/lib/api";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

// ─── Initial demo messages (mock mode only) ───────────────────────────────────

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
      explanation:
        "Seit 2023 gesetzlich klar geregelt in § 4 Abs. 5 Nr. 6b EStG.",
    },
    savingAmount: 252,
    timestamp: new Date(),
  },
];

// ─── Context types ────────────────────────────────────────────────────────────

export interface SavingEntry {
  label: string;
  amount: number;
  riskLevel: "low" | "medium" | "high";
}

interface ChatContextValue {
  messages: Message[];
  isLoading: boolean;
  submitMessage: (text: string) => void;
  errorMessage: string | null;
  clearError: () => void;
  sessions: Session[];
  activeSessionId: string;
  selectSession: (id: string) => void;
  newSession: () => void;
  deleteSession: (id: string) => void;
  totalSaving: number;
  savingEntries: SavingEntry[];
  taxYear: number;
  setTaxYear: (year: number) => void;
}

// ─── Context + hook ───────────────────────────────────────────────────────────

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChatContext() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used inside ChatProvider");
  return ctx;
}

// ─── Shared derived-state helper ──────────────────────────────────────────────

function useSavingDerived(messages: Message[]) {
  const savingEntries = useMemo<SavingEntry[]>(
    () =>
      messages
        .filter((m) => m.role === "assistant" && m.savingAmount)
        .map((m) => ({
          label: m.content.split("\n")[0].slice(0, 65),
          amount: m.savingAmount!,
          riskLevel: m.riskBadge?.level ?? "low",
        })),
    [messages],
  );

  const totalSaving = useMemo(
    () => savingEntries.reduce((sum, e) => sum + e.amount, 0),
    [savingEntries],
  );

  return { savingEntries, totalSaving };
}

// ─── Mock Provider ────────────────────────────────────────────────────────────

function MockProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>(MOCK_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string>(
    MOCK_SESSIONS[0].id,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const clearError = useCallback(() => setErrorMessage(null), []);
  const [taxYear, setTaxYear] = useState(2025);

  const { messages, isLoading, submitMessage } = useMockChat({
    initialMessages: INITIAL_MESSAGES,
  });

  const { savingEntries, totalSaving } = useSavingDerived(messages);

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  const newSession = useCallback(() => {
    const id = `session-${Date.now()}`;
    setSessions((prev) => [
      { id, title: "Neue Konversation", createdAt: new Date(), messageCount: 0 },
      ...prev,
    ]);
    setActiveSessionId(id);
  }, []);

  const deleteSess = useCallback((id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    setActiveSessionId((cur) =>
      cur === id ? `session-${Date.now()}` : cur,
    );
  }, []);

  // Derive active session stats without storing back into state
  const sessionsWithStats = useMemo(
    () =>
      sessions.map((s) =>
        s.id === activeSessionId
          ? { ...s, messageCount: messages.length, totalSaving }
          : s,
      ),
    [sessions, activeSessionId, messages.length, totalSaving],
  );

  return (
    <ChatContext.Provider
      value={{
        messages,
        isLoading,
        submitMessage,
        errorMessage,
        clearError,
        sessions: sessionsWithStats,
        activeSessionId,
        selectSession,
        newSession,
        deleteSession: deleteSess,
        totalSaving,
        savingEntries,
        taxYear,
        setTaxYear,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

// ─── API Provider ─────────────────────────────────────────────────────────────

function APIProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>(
    () => crypto.randomUUID(),
  );
  const [extraError, setExtraError] = useState<string | null>(null);
  const [taxYear, setTaxYear] = useState(2025);

  const refreshSessions = useCallback(() => {
    fetchSessions()
      .then(setSessions)
      .catch((err: unknown) =>
        setExtraError(
          err instanceof Error ? err.message : "Sessions konnten nicht geladen werden",
        ),
      );
  }, []);

  // Load sessions on mount
  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const {
    messages,
    isLoading,
    submitMessage,
    errorMessage: apiError,
    resetMessages,
  } = useChatAPI({ sessionId: activeSessionId, taxYear, onDone: refreshSessions });

  const errorMessage = apiError ?? extraError;
  const clearError = useCallback(() => {
    setExtraError(null);
  }, []);

  const { savingEntries, totalSaving } = useSavingDerived(messages);

  const selectSession = useCallback(
    async (id: string) => {
      setActiveSessionId(id);
      try {
        const msgs = await fetchSessionMessages(id);
        resetMessages(msgs);
      } catch {
        resetMessages([]);
      }
    },
    [resetMessages],
  );

  const newSession = useCallback(() => {
    const id = crypto.randomUUID();
    setActiveSessionId(id);
    resetMessages([]);
  }, [resetMessages]);

  const deleteSess = useCallback(
    async (id: string) => {
      await apiDeleteSession(id).catch(() => null);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        const next = crypto.randomUUID();
        setActiveSessionId(next);
        resetMessages([]);
      }
    },
    [activeSessionId, resetMessages],
  );

  return (
    <ChatContext.Provider
      value={{
        messages,
        isLoading,
        submitMessage,
        errorMessage,
        clearError,
        sessions,
        activeSessionId,
        selectSession,
        newSession,
        deleteSession: deleteSess,
        totalSaving,
        savingEntries,
        taxYear,
        setTaxYear,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

// ─── Public ChatProvider (picks implementation based on USE_MOCK) ─────────────

export function ChatProvider({ children }: { children: React.ReactNode }) {
  return USE_MOCK ? (
    <MockProvider>{children}</MockProvider>
  ) : (
    <APIProvider>{children}</APIProvider>
  );
}
