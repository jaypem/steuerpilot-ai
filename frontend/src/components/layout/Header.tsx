interface HeaderProps {
  onToggleSessionSidebar: () => void;
  onToggleSparSidebar: () => void;
}

export default function Header({
  onToggleSessionSidebar,
  onToggleSparSidebar,
}: HeaderProps) {
  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface-raised px-4">
      {/* Mobile: Session-Sidebar-Toggle */}
      <button
        onClick={onToggleSessionSidebar}
        aria-label="Konversations-Verlauf öffnen"
        className="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-border lg:hidden"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
          <rect y="3" width="18" height="1.5" rx="0.75" fill="currentColor" />
          <rect y="8.25" width="18" height="1.5" rx="0.75" fill="currentColor" />
          <rect y="13.5" width="18" height="1.5" rx="0.75" fill="currentColor" />
        </svg>
      </button>

      {/* Logo */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm font-semibold tracking-tight text-foreground">
          steuerpilot
        </span>
        <span className="rounded-full bg-accent-subtle px-2 py-0.5 font-mono text-xs font-medium text-accent">
          2025
        </span>
      </div>

      {/* Mobile: Spar-Sidebar-Toggle */}
      <button
        onClick={onToggleSparSidebar}
        aria-label="Sparpotenzial öffnen"
        className="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-border lg:hidden"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
          <path
            d="M9 1.5C4.86 1.5 1.5 4.86 1.5 9S4.86 16.5 9 16.5 16.5 13.14 16.5 9 13.14 1.5 9 1.5Zm.75 11.25H8.25V8.25h1.5v4.5Zm0-6H8.25v-1.5h1.5v1.5Z"
            fill="currentColor"
          />
        </svg>
      </button>

      {/* Desktop: Platzhalter rechts für symmetrisches Layout */}
      <div className="hidden w-8 lg:block" aria-hidden />
    </header>
  );
}
