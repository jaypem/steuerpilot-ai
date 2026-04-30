"use client";

import { useState, useRef, useEffect } from "react";
import { useChatContext } from "@/context/ChatContext";
import { formatRelativeDate } from "@/lib/mockSessions";

function SessionTitle({
  id,
  title,
}: {
  id: string;
  title: string;
}) {
  const { renameSession } = useChatContext();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  function commit() {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== title) renameSession(id, trimmed);
    else setDraft(title);
    setEditing(false);
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") { setDraft(title); setEditing(false); }
        }}
        onClick={(e) => e.stopPropagation()}
        className="w-full truncate rounded bg-transparent text-sm outline outline-1 outline-accent px-0.5 -mx-0.5"
      />
    );
  }

  return (
    <span
      className="truncate text-sm flex-1"
      onDoubleClick={(e) => { e.stopPropagation(); setDraft(title); setEditing(true); }}
      title="Doppelklick zum Umbenennen"
    >
      {title}
    </span>
  );
}

export default function SessionSidebar() {
  const { sessions, activeSessionId, selectSession, newSession, taxYear, setTaxYear } =
    useChatContext();

  return (
    <aside
      className="flex h-full w-64 shrink-0 flex-col bg-sidebar"
      aria-label="Konversations-Verlauf"
    >
      {/* Logo */}
      <div className="flex h-12 shrink-0 items-center border-b border-sidebar-item px-4">
        <span className="font-mono text-sm font-semibold tracking-tight text-white">
          steuerpilot
        </span>
        <select
          value={taxYear}
          onChange={(e) => setTaxYear(Number(e.target.value))}
          aria-label="Steuerjahr auswählen"
          className="ml-auto rounded-full bg-accent px-2 py-0.5 font-mono text-xs font-medium text-white cursor-pointer appearance-none text-center"
        >
          {[2023, 2024, 2025].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Neue Konversation */}
      <div className="px-3 pt-3">
        <button
          onClick={newSession}
          className="flex w-full items-center gap-2 rounded-md border border-sidebar-item px-3 py-2 text-sm text-sidebar-text transition-colors hover:border-sidebar-text-active hover:text-sidebar-text-active"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path
              d="M7 1v12M1 7h12"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
          Neue Konversation
        </button>
      </div>

      {/* Session-Liste */}
      <nav
        className="flex-1 overflow-y-auto px-3 pt-4"
        aria-label="Gespeicherte Konversationen"
      >
        <p className="mb-2 px-1 text-xs font-medium uppercase tracking-wider text-muted">
          Verlauf
        </p>
        <ul className="flex flex-col gap-1">
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <li key={session.id}>
                <button
                  onClick={() => selectSession(session.id)}
                  aria-current={isActive ? "page" : undefined}
                  className={`group flex w-full flex-col rounded-md px-3 py-2 text-left transition-colors ${isActive
                      ? "bg-sidebar-item-active text-white"
                      : "text-sidebar-text hover:bg-sidebar-item hover:text-sidebar-text-active"
                    }`}
                >
                  <SessionTitle id={session.id} title={session.title} />
                  <div className="mt-0.5 flex items-center justify-between gap-2">
                    <span className="text-xs opacity-60">
                      {formatRelativeDate(session.createdAt)}
                    </span>
                    {session.totalSaving != null && session.totalSaving > 0 && (
                      <span className="text-xs font-medium text-saving">
                        {session.totalSaving.toLocaleString("de-DE")} €
                      </span>
                    )}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="shrink-0 border-t border-sidebar-item px-4 py-3">
        <p className="text-xs leading-relaxed text-muted">
          Kein zugelassener Steuerberater.
          <br />
          Angaben ohne Gewähr.
        </p>
      </div>
    </aside>
  );
}
