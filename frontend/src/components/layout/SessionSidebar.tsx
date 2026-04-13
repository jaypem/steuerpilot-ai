"use client";

interface MockSession {
  id: string;
  title: string;
  date: string;
  saving?: number;
}

const mockSessions: MockSession[] = [
  { id: "1", title: "Homeoffice & Arbeitsmittel", date: "heute", saving: 847 },
  { id: "2", title: "Pendlerpauschale 2024", date: "gestern", saving: 420 },
  { id: "3", title: "Erste Steuererklärung", date: "vor 3 Tagen", saving: 210 },
];

interface SessionSidebarProps {
  activeSessionId?: string;
  onSelectSession?: (id: string) => void;
  onNewSession?: () => void;
}

export default function SessionSidebar({
  activeSessionId,
  onSelectSession,
  onNewSession,
}: SessionSidebarProps) {
  return (
    <aside
      className="flex h-full w-64 shrink-0 flex-col bg-sidebar"
      aria-label="Konversations-Verlauf"
    >
      {/* Logo */}
      <div className="flex h-12 shrink-0 items-center px-4 border-b border-sidebar-item">
        <span className="font-mono text-sm font-semibold text-white tracking-tight">
          steuerpilot
        </span>
        <span className="ml-2 rounded-full bg-accent px-2 py-0.5 font-mono text-xs font-medium text-white">
          2025
        </span>
      </div>

      {/* Neue Konversation */}
      <div className="px-3 pt-3">
        <button
          onClick={onNewSession}
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
      <nav className="flex-1 overflow-y-auto px-3 pt-4" aria-label="Gespeicherte Konversationen">
        <p className="mb-2 px-1 text-xs font-medium uppercase tracking-wider text-muted">
          Verlauf
        </p>
        <ul className="flex flex-col gap-1">
          {mockSessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <li key={session.id}>
                <button
                  onClick={() => onSelectSession?.(session.id)}
                  className={`group flex w-full flex-col rounded-md px-3 py-2 text-left transition-colors ${
                    isActive
                      ? "bg-sidebar-item-active text-white"
                      : "text-sidebar-text hover:bg-sidebar-item hover:text-sidebar-text-active"
                  }`}
                  aria-current={isActive ? "page" : undefined}
                >
                  <span className="truncate text-sm">{session.title}</span>
                  <div className="mt-0.5 flex items-center justify-between">
                    <span className="text-xs opacity-60">{session.date}</span>
                    {session.saving && (
                      <span className="text-xs font-medium text-saving">
                        {session.saving} €
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
        <p className="text-xs text-muted leading-relaxed">
          Kein zugelassener Steuerberater.
          <br />
          Angaben ohne Gewähr.
        </p>
      </div>
    </aside>
  );
}
