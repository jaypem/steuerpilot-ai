"use client";

import { useEffect, useRef, useState } from "react";
import { useChatContext } from "@/context/ChatContext";

function AnimatedNumber({ value }: { value: number }) {
  const [highlighted, setHighlighted] = useState(false);
  const prevRef = useRef(value);

  useEffect(() => {
    if (value !== prevRef.current) {
      prevRef.current = value;
      // Defer both state updates so they are not synchronous within the effect
      const onId = setTimeout(() => setHighlighted(true), 0);
      const offId = setTimeout(() => setHighlighted(false), 800);
      return () => { clearTimeout(onId); clearTimeout(offId); };
    }
  }, [value]);

  return (
    <span
      className={`font-mono text-3xl font-bold transition-colors duration-300 ${
        highlighted ? "text-saving" : "text-saving"
      }`}
      style={{
        filter: highlighted ? "drop-shadow(0 0 6px var(--color-saving))" : "none",
        transition: "filter 0.4s ease",
      }}
    >
      {value.toLocaleString("de-DE")} €
    </span>
  );
}

export default function SparSidebar() {
  const { totalSaving, savingEntries, taxPrepItems } = useChatContext();

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
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted">
          Geschätzte Ersparnis
        </p>
        <AnimatedNumber value={totalSaving} />
        <p className="mt-1 text-xs text-muted">
          Summe aller Empfehlungen dieser Session
        </p>
      </div>

      {/* Positions-Liste */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {savingEntries.length === 0 && taxPrepItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-saving-subtle">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
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
          <div className="space-y-5">
            {savingEntries.length > 0 && (
              <section>
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">
                  Empfehlungen
                </p>
                <ul className="flex flex-col gap-2">
                  {savingEntries.map((entry, i) => (
                    <li
                      key={i}
                      className="rounded-lg border border-border bg-surface p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs leading-relaxed text-foreground line-clamp-2">
                          {entry.label}
                        </p>
                        <span className="shrink-0 font-mono text-sm font-semibold text-saving">
                          {entry.amount.toLocaleString("de-DE")} €
                        </span>
                      </div>
                      <div className="mt-1.5 flex items-center gap-1">
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            entry.riskLevel === "low"
                              ? "bg-risk-low"
                              : entry.riskLevel === "medium"
                                ? "bg-risk-medium"
                                : "bg-risk-high"
                          }`}
                          aria-hidden
                        />
                        <span className="text-xs text-muted">
                          {entry.riskLevel === "low"
                            ? "Unstreitig"
                            : entry.riskLevel === "medium"
                              ? "Grauzone"
                              : "Strittig"}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {taxPrepItems.length > 0 && (
              <section>
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">
                  Übernommene Steuerchancen
                </p>
                <ul className="flex flex-col gap-2">
                  {taxPrepItems.map((item) => (
                    <li
                      key={item.id}
                      className="rounded-lg border border-border bg-surface p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs leading-relaxed text-foreground line-clamp-2">
                          {item.title}
                        </p>
                        <span className="shrink-0 font-mono text-sm font-semibold text-saving">
                          {item.estimatedSavingEur != null
                            ? `${item.estimatedSavingEur.toLocaleString("de-DE")} €`
                            : "—"}
                        </span>
                      </div>
                      <div className="mt-1.5 flex items-center gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-risk-low" aria-hidden />
                        <span className="text-xs text-muted">Instagram-Check</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
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
