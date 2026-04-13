import type { Session } from "@/types/session";

export const MOCK_SESSIONS: Session[] = [
  {
    id: "session-1",
    title: "Homeoffice & Arbeitsmittel",
    createdAt: new Date(Date.now() - 0),
    messageCount: 4,
    totalSaving: 672,
  },
  {
    id: "session-2",
    title: "Pendlerpauschale 2025",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24),
    messageCount: 6,
    totalSaving: 403,
  },
  {
    id: "session-3",
    title: "Handwerkerleistungen",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3),
    messageCount: 3,
    totalSaving: 1200,
  },
  {
    id: "session-4",
    title: "Erste Steuererklärung",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
    messageCount: 10,
    totalSaving: 210,
  },
];

export function formatRelativeDate(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "heute";
  if (diffDays === 1) return "gestern";
  if (diffDays < 7) return `vor ${diffDays} Tagen`;
  if (diffDays < 14) return "vor einer Woche";
  return date.toLocaleDateString("de-DE", { day: "numeric", month: "short" });
}
