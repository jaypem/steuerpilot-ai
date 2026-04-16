import type { Message, RiskBadge, Source } from "@/types/chat";
import type { Session } from "@/types/session";
import type { ScanResult } from "@/types/scan";
import { parseSSEStream } from "./sseParser";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Backend payload types ────────────────────────────────────────────────────

interface ChatPayload {
  message: string;
  session_id?: string;
  tax_year?: number;
}

export type StreamChunk =
  | { type: "text"; content: string }
  | {
      type: "source";
      law: string;
      paragraph: string;
      section: string;
      text: string;
      url?: string | null;
    }
  | {
      type: "risk_badge";
      level: "low" | "medium" | "high";
      label: string;
      explanation: string;
    }
  | { type: "saving"; amount: number }
  | { type: "done" }
  | { type: "error"; message: string };

interface APISession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  total_saving: number;
}

interface APIMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources: Array<Source> | null;
  risk_badge: RiskBadge | null;
  saving_amount: number | null;
  created_at: string;
}

interface APISessionDetail extends APISession {
  messages: APIMessage[];
}

// ─── Mappers ──────────────────────────────────────────────────────────────────

function mapSession(s: APISession): Session {
  return {
    id: s.id,
    title: s.title,
    createdAt: new Date(s.created_at),
    messageCount: s.message_count,
    totalSaving: s.total_saving || undefined,
  };
}

function mapMessage(m: APIMessage): Message {
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    sources: m.sources ?? undefined,
    riskBadge: m.risk_badge ?? undefined,
    savingAmount: m.saving_amount ?? undefined,
    timestamp: new Date(m.created_at),
  };
}

// ─── API calls ────────────────────────────────────────────────────────────────

export async function* streamChat(
  payload: ChatPayload,
  signal?: AbortSignal,
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  if (!response.body) {
    throw new Error("Response body is empty");
  }

  yield* parseSSEStream<StreamChunk>(response.body);
}

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/api/sessions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data: APISession[] = await res.json();
  return data.map(mapSession);
}

export async function fetchSessionMessages(
  sessionId: string,
): Promise<Message[]> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data: APISessionDetail = await res.json();
  return data.messages.map(mapMessage);
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 404) throw new Error(`HTTP ${res.status}`);
}

export async function scanExpenses(
  expenses: Array<{ description: string; amount: number }>,
  context?: string,
  taxYear = 2025,
): Promise<ScanResult> {
  const res = await fetch(`${API_URL}/api/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      expenses,
      context: context?.trim() || null,
      tax_year: taxYear,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Scan fehlgeschlagen (${res.status}): ${text}`);
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data: any = await res.json();
  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    items: data.items.map((item: any) => ({
      description: item.description,
      amount: item.amount,
      deductible: item.deductible,
      deductibleAmount: item.deductible_amount,
      savingEstimate: item.saving_estimate,
      risk: item.risk,
      explanation: item.explanation,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      sources: (item.sources ?? []).map((s: any) => ({
        law: s.law,
        paragraph: s.paragraph,
        section: s.section ?? "",
      })),
    })),
    totalSavingEstimate: data.total_saving_estimate,
    missingPositions: data.missing_positions ?? [],
  };
}
