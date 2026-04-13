interface SparSidebarProps {
  totalSaving?: number;
}

export default function SparSidebar({ totalSaving = 0 }: SparSidebarProps) {
  return (
    <aside
      className="flex h-full w-72 shrink-0 flex-col border-l border-border bg-surface-raised"
      aria-label="Sparpotenzial"
    >
      {/* Header */}
      <div className="flex h-12 shrink-0 items-center border-b border-border px-4">
        <h2 className="text-sm font-semibold text-foreground">Sparpotenzial</h2>
      </div>

      {/* Gesamt-Ersparnis */}
      <div className="border-b border-border px-4 py-4">
        <p className="text-xs font-medium uppercase tracking-wider text-muted mb-1">
          Geschätzte Ersparnis
        </p>
        <p className="font-mono text-3xl font-bold text-saving">
          {totalSaving.toLocaleString("de-DE")} €
        </p>
        <p className="mt-1 text-xs text-muted">
          Summe aller Empfehlungen dieser Session
        </p>
      </div>

      {/* Positions-Liste (Platzhalter) */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {totalSaving === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-saving-subtle">
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                aria-hidden
              >
                <path
                  d="M10 2a8 8 0 1 0 0 16A8 8 0 0 0 10 2Zm1 11H9v-4h2v4Zm0-6H9V5h2v2Z"
                  fill="var(--color-saving)"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-foreground">
              Noch keine Empfehlungen
            </p>
            <p className="mt-1 text-xs text-muted">
              Stelle eine Frage zur Steuererklärung, um Sparpotenziale zu
              entdecken.
            </p>
          </div>
        ) : (
          <p className="text-xs text-muted">Positionen folgen in Phase 5.</p>
        )}
      </div>

      {/* Disclaimer */}
      <div className="shrink-0 border-t border-border px-4 py-3">
        <p className="text-xs leading-relaxed text-muted">
          Schätzwerte. Kein Ersatz für steuerliche Beratung gem. StBerG.
        </p>
      </div>
    </aside>
  );
}
