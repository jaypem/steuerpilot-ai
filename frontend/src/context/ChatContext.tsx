"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useChatAPI } from "@/hooks/useChatAPI";
import { useMockChat } from "@/hooks/useMockChat";
import {
  fetchTaxPrepItems,
  deleteSession as apiDeleteSession,
  fetchSessionMessages,
  fetchSessions,
  renameSession as apiRenameSession,
} from "@/lib/api";
import {
  DOUBLE_TAX_SAVINGS_INFO_URL,
  DOUBLE_TAX_SAVINGS_LABEL,
  DOUBLE_TAX_SAVINGS_ROUTE,
} from "@/lib/doubleTaxSavings";
import { getMockIdeaTransferCase } from "@/lib/mockIdeaTransfer";
import {
  fetchMockTaxPrepItems,
} from "@/lib/mockInstagramCheck";
import { MOCK_SESSIONS } from "@/lib/mockSessions";
import type { Message, RiskBadge } from "@/types/chat";
import type { TaxPrepItem } from "@/types/instagramCheck";
import type {
  IdeaTransferAnswers,
  IdeaTransferCaseKind,
  IdeaTransferEvaluationResult,
  IdeaTransferOriginScope,
} from "@/types/ideaTransfer";
import type { Session } from "@/types/session";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

const IDEA_TRANSFER_QUESTION_1 =
  "Gab es in diesem Steuerjahr eine Idee oder Erfindung oder einen geplanten Verkauf an die eigene GmbH oder in der Familie?";
const IDEA_TRANSFER_QUESTION_2 =
  "Ist die Idee privat entstanden oder im Rahmen von Anstellung oder Selbststaendigkeit?";
const IDEA_TRANSFER_SESSION_PREFIX = DOUBLE_TAX_SAVINGS_LABEL;
const LEGACY_IDEA_TRANSFER_SESSION_PREFIX = "Ideen-Transfer";

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
      "Ja, Homeoffice-Kosten koennen Sie steuerlich geltend machen. Seit 2023 gilt die erhoehte Tagespauschale von 6 EUR pro Tag (max. 1.260 EUR im Jahr, also 210 Tage).\n\nAlternativ koennen Sie ein haeusliches Arbeitszimmer absetzen, wenn es ausschliesslich beruflich genutzt wird - dann sind die tatsaechlichen anteiligen Kosten absetzbar, was bei groesseren Wohnungen deutlich mehr einbringen kann.\n\nHaben Sie auch Arbeitsmittel wie Laptop, Monitor oder Buerostuhl gekauft?",
    sources: [
      {
        law: "EStG",
        paragraph: "§ 4",
        section: "Abs. 5 Nr. 6b",
        text: "Fuer jeden Kalendertag, an dem der Steuerpflichtige seine betriebliche oder berufliche Taetigkeit ausschliesslich in der haeuslichen Wohnung ausuebt, kann er einen Betrag von 6 Euro abziehen, hoechstens 1 260 Euro im Wirtschafts- oder Kalenderjahr.",
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

export interface SavingEntry {
  label: string;
  amount: number;
  riskLevel: "low" | "medium" | "high";
}

interface QuickReplyOption {
  id: string;
  label: string;
}

interface IdeaTransferOnboardingView {
  transcript: Message[];
  quickReplies: QuickReplyOption[];
  ctaHref?: string;
  ctaLabel?: string;
}

type IdeaTransferOnboardingStage =
  | "question1"
  | "question2"
  | "cta"
  | "dismissed";

interface IdeaTransferOnboardingRecord {
  stage: IdeaTransferOnboardingStage;
  transcript: Message[];
  prefill: {
    caseKind?: IdeaTransferCaseKind;
    answers: Partial<IdeaTransferAnswers>;
  };
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
  renameSession: (id: string, title: string) => void;
  isMockMode: boolean;
  refreshSessions: () => Promise<void>;
  reloadActiveSession: () => Promise<void>;
  taxPrepItems: TaxPrepItem[];
  refreshTaxPrepItems: () => Promise<void>;
  ideaTransferOnboarding: IdeaTransferOnboardingView | null;
  answerIdeaTransferOnboarding: (choiceId: string) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChatContext() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used inside ChatProvider");
  return ctx;
}

function useSavingDerived(messages: Message[]) {
  const savingEntries = useMemo<SavingEntry[]>(
    () =>
      messages
        .filter((message) => message.role === "assistant" && message.savingAmount)
        .map((message) => ({
          label: message.content.split("\n")[0].slice(0, 65),
          amount: message.savingAmount!,
          riskLevel: message.riskBadge?.level ?? "low",
        })),
    [messages],
  );

  const totalSaving = useMemo(
    () => savingEntries.reduce((sum, entry) => sum + entry.amount, 0),
    [savingEntries],
  );

  return { savingEntries, totalSaving };
}

function createLocalMessage(
  sessionId: string,
  role: Message["role"],
  content: string,
): Message {
  return {
    id: `intro-${sessionId}-${crypto.randomUUID()}`,
    role,
    content,
    timestamp: new Date(),
  };
}

function caseTitle(caseKind: IdeaTransferCaseKind): string {
  return caseKind === "own_gmbh_sale"
    ? `${DOUBLE_TAX_SAVINGS_LABEL} GmbH`
    : `${DOUBLE_TAX_SAVINGS_LABEL} Familie`;
}

function inferCaseKindFromTitle(title?: string): IdeaTransferCaseKind | undefined {
  if (
    !title?.startsWith(IDEA_TRANSFER_SESSION_PREFIX) &&
    !title?.startsWith(LEGACY_IDEA_TRANSFER_SESSION_PREFIX)
  ) {
    return undefined;
  }
  if (title.includes("Familie")) return "family_transfer";
  return "own_gmbh_sale";
}

function buildIdeaTransferHref(
  prefill: IdeaTransferOnboardingRecord["prefill"],
): string {
  const params = new URLSearchParams();
  if (prefill.caseKind) params.set("case_kind", prefill.caseKind);
  if (prefill.answers.originScope) {
    params.set("origin_scope", prefill.answers.originScope);
  }
  const query = params.toString();
  return query ? `${DOUBLE_TAX_SAVINGS_ROUTE}?${query}` : DOUBLE_TAX_SAVINGS_ROUTE;
}

function createInitialOnboardingRecord(
  sessionId: string,
  sessionTitle?: string,
): IdeaTransferOnboardingRecord {
  const caseKind = inferCaseKindFromTitle(sessionTitle);
  if (caseKind) {
    return {
      stage: "cta",
      transcript: [
        createLocalMessage(
          sessionId,
          "assistant",
          `Zu dieser Session gehoert bereits ein [${DOUBLE_TAX_SAVINGS_LABEL}](${DOUBLE_TAX_SAVINGS_INFO_URL})-Fall. Oeffnen Sie den strukturierten Check, um Angaben zu pruefen oder zu ergaenzen.`,
        ),
      ],
      prefill: { caseKind, answers: {} },
    };
  }

  return {
    stage: "question1",
    transcript: [createLocalMessage(sessionId, "assistant", IDEA_TRANSFER_QUESTION_1)],
    prefill: { answers: {} },
  };
}

function toOnboardingView(
  record: IdeaTransferOnboardingRecord | null,
): IdeaTransferOnboardingView | null {
  if (!record || record.stage === "dismissed") return null;

  if (record.stage === "question1") {
    return {
      transcript: record.transcript,
      quickReplies: [
        { id: "own_gmbh_sale", label: "Ja, eigene GmbH" },
        { id: "family_transfer", label: "Ja, Familie" },
        { id: "none", label: "Nein" },
        { id: "not_sure", label: "Nicht sicher" },
      ],
    };
  }

  if (record.stage === "question2") {
    return {
      transcript: record.transcript,
      quickReplies: [
        { id: "private", label: "Privat" },
        { id: "professional", label: "Beruflich/Dienstlich" },
        { id: "unclear", label: "Unklar" },
      ],
    };
  }

  return {
    transcript: record.transcript,
    quickReplies: [],
    ctaHref: buildIdeaTransferHref(record.prefill),
    ctaLabel: `Zum ${DOUBLE_TAX_SAVINGS_LABEL}-Check`,
  };
}

function advanceOnboarding(
  sessionId: string,
  sessionTitle: string | undefined,
  current: IdeaTransferOnboardingRecord | undefined,
  choiceId: string,
): IdeaTransferOnboardingRecord {
  const record = current ?? createInitialOnboardingRecord(sessionId, sessionTitle);

  if (record.stage === "question1") {
    const transcript = [
      ...record.transcript,
      createLocalMessage(
        sessionId,
        "user",
        choiceId === "own_gmbh_sale"
          ? "Ja, eigene GmbH"
          : choiceId === "family_transfer"
            ? "Ja, Familie"
            : choiceId === "none"
              ? "Nein"
              : "Nicht sicher",
      ),
    ];

    if (choiceId === "none") {
      return {
        stage: "dismissed",
        transcript: [
          ...transcript,
          createLocalMessage(
            sessionId,
            "assistant",
            "Verstanden. Dann lassen wir diesen Spezialfall fuer diese Session aus und konzentrieren uns auf die normale Steuererklaerung.",
          ),
        ],
        prefill: { answers: {} },
      };
    }

    return {
      stage: "question2",
      transcript: [
        ...transcript,
        createLocalMessage(sessionId, "assistant", IDEA_TRANSFER_QUESTION_2),
      ],
      prefill: {
        caseKind:
          choiceId === "own_gmbh_sale" || choiceId === "family_transfer"
            ? choiceId
            : undefined,
        answers: {},
      },
    };
  }

  if (record.stage === "question2") {
    const originScope = choiceId as IdeaTransferOriginScope;
    const transcript = [
      ...record.transcript,
      createLocalMessage(
        sessionId,
        "user",
        choiceId === "private"
          ? "Privat"
          : choiceId === "professional"
            ? "Beruflich/Dienstlich"
            : "Unklar",
      ),
    ];

    const assistantCopy =
      choiceId === "professional"
        ? "Das ist ein deutlicher Warnhinweis fuer den Spezialfall. Sie koennen den strukturierten Check trotzdem oeffnen und die Punkte geordnet dokumentieren."
        : choiceId === "private"
          ? "Dann lohnt sich ein strukturierter Vorab-Check. Dort koennen Sie Falltyp, Bewertung, Gegenleistung und Dokumentation geordnet pruefen."
          : "Dann ist ein strukturierter Vorab-Check sinnvoll, um die kritischen Voraussetzungen sauber abzuarbeiten.";

    return {
      stage: "cta",
      transcript: [
        ...transcript,
        createLocalMessage(sessionId, "assistant", assistantCopy),
      ],
      prefill: {
        caseKind: record.prefill.caseKind,
        answers: {
          ...record.prefill.answers,
          originScope,
        },
      },
    };
  }

  return record;
}

function riskBadgeForTrafficLight(
  trafficLight: IdeaTransferEvaluationResult["trafficLight"],
): RiskBadge {
  if (trafficLight === "green") {
    return {
      level: "low",
      label: "Plausibel pruefbar",
      explanation:
        "Der Spezialfall wirkt nach den aktuellen Angaben strukturell nachvollziehbar.",
    };
  }
  if (trafficLight === "yellow") {
    return {
      level: "medium",
      label: "Nur mit Zusatzpruefung",
      explanation:
        "Bewertung, Dokumentation oder Wertgleichheit sind noch nicht vollstaendig belastbar.",
    };
  }
  return {
    level: "high",
    label: "Derzeit nicht tragfaehig",
    explanation:
      "Mindestens ein harter Blocker spricht aktuell gegen die Struktur.",
  };
}

function buildIdeaTransferSummaryMessage(
  sessionId: string,
  result: IdeaTransferEvaluationResult,
): Message {
  return {
    id: `idea-transfer-summary-${sessionId}`,
    role: "assistant",
    content: result.summaryMarkdown,
    sources: result.sources,
    riskBadge: riskBadgeForTrafficLight(result.trafficLight),
    savingAmount: result.estimatedTaxBenefitMidEur ?? undefined,
    timestamp: new Date(),
  };
}

function buildInstagramPrepSummaryMessage(
  sessionId: string,
  items: TaxPrepItem[],
): Message {
  const total = items.reduce((sum, item) => sum + (item.estimatedSavingEur ?? 0), 0);
  const lines = [
    "## Instagram-Check: uebernommene Steuerchancen",
    "",
    `**Bestaetigte Tipps:** ${items.length}`,
    `**Geschaetzte Gesamtersparnis:** ${total.toLocaleString("de-DE")} EUR`,
    "",
    ...items.map((item) => `- **${item.title}:** ${item.summary}`),
  ];

  return {
    id: `instagram-summary-${sessionId}`,
    role: "assistant",
    content: lines.join("\n"),
    riskBadge: {
      level: "low",
      label: "Vorpruefung uebernommen",
      explanation: "Nur gruene und bestaetigte Instagram-Tipps wurden uebernommen.",
    },
    savingAmount: total || undefined,
    timestamp: new Date(),
  };
}

function MockProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>(MOCK_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string>(
    MOCK_SESSIONS[0].id,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [taxYear, setTaxYear] = useState(2025);
  const [taxPrepItems, setTaxPrepItems] = useState<TaxPrepItem[]>([]);
  const [onboardingBySession, setOnboardingBySession] = useState<
    Record<string, IdeaTransferOnboardingRecord>
  >({});
  const clearError = useCallback(() => setErrorMessage(null), []);
  const demoSessionIds = useMemo(
    () => new Set(MOCK_SESSIONS.map((session) => session.id)),
    [],
  );

  const { messages, isLoading, submitMessage, resetMessages } = useMockChat({
    initialMessages: INITIAL_MESSAGES,
  });

  const currentSessionTitle = useMemo(
    () => sessions.find((session) => session.id === activeSessionId)?.title,
    [sessions, activeSessionId],
  );

  const loadMockSessionMessages = useCallback(
    async (sessionId: string) => {
      const ideaCase = await getMockIdeaTransferCase(sessionId);
      if (ideaCase?.result) {
        resetMessages([buildIdeaTransferSummaryMessage(sessionId, ideaCase.result)]);
        return;
      }

      const prepItems = await fetchMockTaxPrepItems(sessionId);
      if (prepItems.length > 0) {
        resetMessages([buildInstagramPrepSummaryMessage(sessionId, prepItems)]);
        return;
      }

      resetMessages(demoSessionIds.has(sessionId) ? INITIAL_MESSAGES : []);
    },
    [demoSessionIds, resetMessages],
  );

  const { savingEntries, totalSaving } = useSavingDerived(messages);

  const refreshTaxPrepItems = useCallback(async () => {
    setTaxPrepItems(await fetchMockTaxPrepItems(activeSessionId));
  }, [activeSessionId]);

  const refreshSessions = useCallback(async () => {
    const nextSessions = await Promise.all(
      sessions.map(async (session) => {
        const ideaCase = await getMockIdeaTransferCase(session.id);
        const prepItems = await fetchMockTaxPrepItems(session.id);
        const prepSaving = prepItems.reduce(
          (sum, item) => sum + (item.estimatedSavingEur ?? 0),
          0,
        );
        if (!ideaCase) {
          return prepItems.length > 0
            ? {
                ...session,
                title: session.title === "Neue Konversation" ? "Instagram-Check" : session.title,
                messageCount: 1,
                totalSaving: prepSaving || undefined,
              }
            : session;
        }
        return {
          ...session,
          title: caseTitle(ideaCase.caseKind),
          messageCount: ideaCase.result ? 1 : 0,
          totalSaving: ideaCase.result?.estimatedTaxBenefitMidEur ?? undefined,
        };
      }),
    );
    setSessions(nextSessions);
  }, [sessions]);

  const reloadActiveSession = useCallback(async () => {
    await loadMockSessionMessages(activeSessionId);
    await refreshTaxPrepItems();
  }, [activeSessionId, loadMockSessionMessages, refreshTaxPrepItems]);

  const selectSession = useCallback(
    (id: string) => {
      clearError();
      setActiveSessionId(id);
      void loadMockSessionMessages(id);
      void fetchMockTaxPrepItems(id).then(setTaxPrepItems);
    },
    [clearError, loadMockSessionMessages],
  );

  const newSession = useCallback(() => {
    clearError();
    const id = `session-${Date.now()}`;
    setSessions((prev) => [
      { id, title: "Neue Konversation", createdAt: new Date(), messageCount: 0 },
      ...prev,
    ]);
    setActiveSessionId(id);
    setTaxPrepItems([]);
    resetMessages([]);
  }, [clearError, resetMessages]);

  const deleteSess = useCallback(
    (id: string) => {
      const remaining = sessions.filter((session) => session.id !== id);
      const fallbackSession =
        remaining[0] ??
        {
          id: `session-${Date.now()}`,
          title: "Neue Konversation",
          createdAt: new Date(),
          messageCount: 0,
        };
      setSessions(
        remaining.length > 0
          ? remaining
          : [fallbackSession],
      );
      setOnboardingBySession((prev) => {
        const { [id]: removed, ...rest } = prev;
        void removed;
        return rest;
      });

      if (activeSessionId === id) {
        setActiveSessionId(fallbackSession.id);
        void loadMockSessionMessages(fallbackSession.id);
        void fetchMockTaxPrepItems(fallbackSession.id).then(setTaxPrepItems);
      }
    },
    [activeSessionId, loadMockSessionMessages, sessions],
  );

  const renameSess = useCallback((id: string, title: string) => {
    setSessions((prev) =>
      prev.map((session) => (session.id === id ? { ...session, title } : session)),
    );
  }, []);

  const answerIdeaTransferOnboarding = useCallback(
    (choiceId: string) => {
      setOnboardingBySession((prev) => ({
        ...prev,
        [activeSessionId]: advanceOnboarding(
          activeSessionId,
          currentSessionTitle,
          prev[activeSessionId],
          choiceId,
        ),
      }));
    },
    [activeSessionId, currentSessionTitle],
  );

  const ideaTransferOnboarding = useMemo(() => {
    if (messages.length > 0) return null;
    return toOnboardingView(
      onboardingBySession[activeSessionId] ??
        createInitialOnboardingRecord(activeSessionId, currentSessionTitle),
    );
  }, [messages.length, onboardingBySession, activeSessionId, currentSessionTitle]);

  const sessionsWithStats = useMemo(
    () =>
      sessions.map((session) =>
        session.id === activeSessionId
          ? { ...session, messageCount: messages.length, totalSaving }
          : session,
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
        renameSession: renameSess,
        totalSaving,
        savingEntries,
        taxYear,
        setTaxYear,
        isMockMode: true,
        refreshSessions,
        reloadActiveSession,
        taxPrepItems,
        refreshTaxPrepItems,
        ideaTransferOnboarding,
        answerIdeaTransferOnboarding,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

function APIProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>(
    () => crypto.randomUUID(),
  );
  const [extraError, setExtraError] = useState<string | null>(null);
  const [taxYear, setTaxYear] = useState(2025);
  const [taxPrepItems, setTaxPrepItems] = useState<TaxPrepItem[]>([]);
  const [onboardingBySession, setOnboardingBySession] = useState<
    Record<string, IdeaTransferOnboardingRecord>
  >({});
  const sessionLoadRef = useRef<AbortController | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await fetchSessions());
    } catch (err: unknown) {
      setExtraError(
        err instanceof Error ? err.message : "Sessions konnten nicht geladen werden",
      );
    }
  }, []);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  const {
    messages,
    isLoading,
    submitMessage,
    errorMessage: apiError,
    clearError: clearAPIError,
    abortStream,
    resetMessages,
  } = useChatAPI({ sessionId: activeSessionId, taxYear, onDone: refreshSessions });

  const errorMessage = apiError ?? extraError;
  const clearError = useCallback(() => {
    setExtraError(null);
    clearAPIError();
  }, [clearAPIError]);

  const { savingEntries, totalSaving } = useSavingDerived(messages);

  const sessionsWithStats = useMemo(
    () =>
      sessions.map((session) =>
        session.id === activeSessionId
          ? { ...session, messageCount: messages.length, totalSaving }
          : session,
      ),
    [sessions, activeSessionId, messages.length, totalSaving],
  );

  const currentSessionTitle = useMemo(
    () => sessionsWithStats.find((session) => session.id === activeSessionId)?.title,
    [sessionsWithStats, activeSessionId],
  );

  const refreshTaxPrepItems = useCallback(async () => {
    try {
      setTaxPrepItems(await fetchTaxPrepItems(activeSessionId));
    } catch (err) {
      setExtraError(
        err instanceof Error
          ? err.message
          : "Steuerchancen konnten nicht geladen werden",
      );
    }
  }, [activeSessionId]);

  const cancelSessionLoad = useCallback(() => {
    sessionLoadRef.current?.abort();
    sessionLoadRef.current = null;
  }, []);

  useEffect(() => cancelSessionLoad, [cancelSessionLoad]);
  useEffect(() => {
    void refreshTaxPrepItems();
  }, [refreshTaxPrepItems]);

  const loadSessionMessages = useCallback(
    async (
      sessionId: string,
      options?: { activate?: boolean; suppressNotFound?: boolean },
    ) => {
      abortStream();
      cancelSessionLoad();
      clearError();

      const controller = new AbortController();
      sessionLoadRef.current = controller;

      if (options?.activate) {
        setActiveSessionId(sessionId);
      }
      resetMessages([]);

      try {
        const nextMessages = await fetchSessionMessages(sessionId, controller.signal);
        if (controller.signal.aborted || sessionLoadRef.current !== controller) return;
        resetMessages(nextMessages);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        if (sessionLoadRef.current !== controller) return;
        const shouldSuppress =
          options?.suppressNotFound &&
          err instanceof Error &&
          err.message === "HTTP 404";
        if (!shouldSuppress) {
          setExtraError(
            err instanceof Error ? err.message : "Session konnte nicht geladen werden",
          );
        }
        resetMessages([]);
      } finally {
        if (sessionLoadRef.current === controller) {
          sessionLoadRef.current = null;
        }
      }
    },
    [abortStream, cancelSessionLoad, clearError, resetMessages],
  );

  const selectSession = useCallback(
    (id: string) => {
      void loadSessionMessages(id, { activate: true });
    },
    [loadSessionMessages],
  );

  const reloadActiveSession = useCallback(async () => {
    await loadSessionMessages(activeSessionId, { suppressNotFound: true });
    await refreshTaxPrepItems();
  }, [activeSessionId, loadSessionMessages, refreshTaxPrepItems]);

  const newSession = useCallback(() => {
    abortStream();
    cancelSessionLoad();
    clearError();
    const id = crypto.randomUUID();
    setActiveSessionId(id);
    setTaxPrepItems([]);
    resetMessages([]);
  }, [abortStream, cancelSessionLoad, clearError, resetMessages]);

  const deleteSess = useCallback(
    async (id: string) => {
      try {
        await apiDeleteSession(id);
      } catch (err) {
        setExtraError(
          err instanceof Error ? err.message : "Session konnte nicht geloescht werden",
        );
        return;
      }

      setOnboardingBySession((prev) => {
        const { [id]: removed, ...rest } = prev;
        void removed;
        return rest;
      });
      setSessions((prev) => prev.filter((session) => session.id !== id));

      if (activeSessionId === id) {
        abortStream();
        cancelSessionLoad();
        clearError();
        const next = crypto.randomUUID();
        setActiveSessionId(next);
        setTaxPrepItems([]);
        resetMessages([]);
      }
    },
    [activeSessionId, abortStream, cancelSessionLoad, clearError, resetMessages],
  );

  const renameSess = useCallback(async (id: string, title: string) => {
    try {
      await apiRenameSession(id, title);
      setSessions((prev) =>
        prev.map((session) => (session.id === id ? { ...session, title } : session)),
      );
    } catch (err) {
      setExtraError(
        err instanceof Error ? err.message : "Session konnte nicht umbenannt werden",
      );
    }
  }, []);

  const answerIdeaTransferOnboarding = useCallback(
    (choiceId: string) => {
      setOnboardingBySession((prev) => ({
        ...prev,
        [activeSessionId]: advanceOnboarding(
          activeSessionId,
          currentSessionTitle,
          prev[activeSessionId],
          choiceId,
        ),
      }));
    },
    [activeSessionId, currentSessionTitle],
  );

  const ideaTransferOnboarding = useMemo(() => {
    if (messages.length > 0) return null;
    return toOnboardingView(
      onboardingBySession[activeSessionId] ??
        createInitialOnboardingRecord(activeSessionId, currentSessionTitle),
    );
  }, [messages.length, onboardingBySession, activeSessionId, currentSessionTitle]);

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
        renameSession: renameSess,
        totalSaving,
        savingEntries,
        taxYear,
        setTaxYear,
        isMockMode: false,
        refreshSessions,
        reloadActiveSession,
        taxPrepItems,
        refreshTaxPrepItems,
        ideaTransferOnboarding,
        answerIdeaTransferOnboarding,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  return USE_MOCK ? (
    <MockProvider>{children}</MockProvider>
  ) : (
    <APIProvider>{children}</APIProvider>
  );
}
