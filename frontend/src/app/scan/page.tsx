"use client";

import Link from "next/link";
import { useState } from "react";
import { useChatContext } from "@/context/ChatContext";
import { scanExpenses } from "@/lib/api";
import type { ScanExpenseItem, ScanResult, ScannedExpense } from "@/types/scan";

// ─── Risk config ──────────────────────────────────────────────────────────────

const RISK_CONFIG = {
  low:    { label: "Unstreitig",  dot: "bg-green-500",  text: "text-green-400",  pill: "bg-green-500/10 text-green-400" },
  medium: { label: "Grauzone",    dot: "bg-yellow-400", text: "text-yellow-400", pill: "bg-yellow-400/10 text-yellow-400" },
  high:   { label: "Strittig",    dot: "bg-red-500",    text: "text-red-400",    pill: "bg-red-500/10 text-red-400" },
} as const;

// ─── ExpenseRow ───────────────────────────────────────────────────────────────

function ExpenseRow({
  item,
  index,
  onUpdate,
  onRemove,
  canRemove,
}: {
  item: ScanExpenseItem;
  index: number;
  onUpdate: (id: string, field: "description" | "amount", value: string) => void;
  onRemove: (id: string) => void;
  canRemove: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-5 shrink-0 text-right font-mono text-xs text-muted">
        {index + 1}.
      </span>
      <input
        type="text"
        placeholder="Beschreibung, z.B. Homeoffice-Pauschale"
        value={item.description}
        onChange={(e) => onUpdate(item.id, "description", e.target.value)}
        className="min-w-0 flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
        maxLength={500}
      />
      <div className="relative shrink-0">
        <input
          type="number"
          placeholder="0,00"
          value={item.amount}
          onChange={(e) => onUpdate(item.id, "amount", e.target.value)}
          min="0"
          step="0.01"
          className="w-28 rounded-md border border-border bg-surface py-2 pl-3 pr-6 text-right text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
        />
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted">
          €
        </span>
      </div>
      <button
        type="button"
        onClick={() => onRemove(item.id)}
        disabled={!canRemove}
        aria-label="Ausgabe entfernen"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted transition-colors hover:bg-border hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
          <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}

// ─── ScannedExpenseCard ───────────────────────────────────────────────────────

function ScannedExpenseCard({ item }: { item: ScannedExpense }) {
  const risk = RISK_CONFIG[item.risk];

  return (
    <div className="rounded-lg border border-border bg-surface-raised p-4">
      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {item.deductible ? (
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-500/15 text-green-400">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
                <path d="M1.5 5.5l2.5 2.5 4.5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          ) : (
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-500/15 text-red-400">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
                <path d="M2 2l6 6M8 2L2 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </span>
          )}
          <span className="text-sm font-medium text-foreground">{item.description}</span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${risk.pill}`}>
            {risk.label}
          </span>
          <span className="font-mono text-xs text-muted">
            {item.amount.toLocaleString("de-DE", { minimumFractionDigits: 2 })} €
          </span>
        </div>
      </div>

      {/* Saving row */}
      {item.deductible && (
        <div className="mt-2 flex flex-wrap gap-4 text-xs">
          <span className="text-muted">
            Absetzbar:{" "}
            <span className="text-foreground">
              {item.deductibleAmount.toLocaleString("de-DE", { minimumFractionDigits: 2 })} €
            </span>
          </span>
          <span className="text-muted">
            Steuerersparnis ca.{" "}
            <span className="font-medium text-saving">
              {item.savingEstimate.toLocaleString("de-DE")} €
            </span>
          </span>
        </div>
      )}

      {/* Explanation */}
      <p className="mt-2 text-xs leading-relaxed text-muted">{item.explanation}</p>

      {/* Sources */}
      {item.sources.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {item.sources.map((s, i) => (
            <span
              key={i}
              className="rounded-md border border-border bg-surface px-2 py-0.5 font-mono text-xs text-muted"
            >
              {s.paragraph} {s.law}{s.section ? ` ${s.section}` : ""}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── ScanPage ─────────────────────────────────────────────────────────────────

let _idCounter = 0;
function newId() {
  return `expense-${++_idCounter}`;
}

export default function ScanPage() {
  const { taxYear } = useChatContext();
  const [items, setItems] = useState<ScanExpenseItem[]>([
    { id: newId(), description: "", amount: "" },
  ]);
  const [context, setContext] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function addRow() {
    setItems((prev) => [...prev, { id: newId(), description: "", amount: "" }]);
  }

  function updateRow(id: string, field: "description" | "amount", value: string) {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, [field]: value } : item)),
    );
  }

  function removeRow(id: string) {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);

    const validExpenses = items
      .map((item) => ({
        description: item.description.trim(),
        amount: parseFloat(item.amount.replace(",", ".")),
      }))
      .filter((e) => e.description && !isNaN(e.amount) && e.amount >= 0);

    if (validExpenses.length === 0) {
      setError("Bitte mindestens eine Ausgabe mit Beschreibung und Betrag eingeben.");
      return;
    }

    setIsLoading(true);
    try {
      const data = await scanExpenses(validExpenses, context || undefined, taxYear);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col bg-surface">
      {/* Page header */}
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-surface-raised px-4">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-xs text-muted transition-colors hover:text-foreground"
          aria-label="Zurück zum Chat"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M9 2L4 7l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Chat
        </Link>
        <span className="text-border">·</span>
        <h1 className="text-sm font-semibold text-foreground">Ausgaben-Scan</h1>
        <span className="rounded-full bg-accent-subtle px-2 py-0.5 font-mono text-xs font-medium text-accent">
          {taxYear}
        </span>
      </header>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-2xl px-4 py-8">

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Expense rows */}
            <section>
              <h2 className="mb-3 text-sm font-medium text-foreground">Ausgaben</h2>
              <div className="space-y-2">
                {items.map((item, index) => (
                  <ExpenseRow
                    key={item.id}
                    item={item}
                    index={index}
                    onUpdate={updateRow}
                    onRemove={removeRow}
                    canRemove={items.length > 1}
                  />
                ))}
              </div>
              <button
                type="button"
                onClick={addRow}
                disabled={items.length >= 50}
                className="mt-3 flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted transition-colors hover:bg-border hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
                  <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                Ausgabe hinzufügen
              </button>
            </section>

            {/* Context */}
            <section>
              <label htmlFor="context" className="mb-1.5 block text-sm font-medium text-foreground">
                Kontext{" "}
                <span className="font-normal text-muted">(optional)</span>
              </label>
              <textarea
                id="context"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="z.B. Ich bin Freiberufler im Homeoffice und nutze das Fahrzeug beruflich."
                maxLength={1000}
                rows={3}
                className="w-full resize-none rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
              />
              <p className="mt-1 text-right text-xs text-muted">
                {context.length}/1000
              </p>
            </section>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {isLoading ? (
                <>
                  <svg
                    className="h-4 w-4 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                    aria-hidden
                  >
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Analysiere Ausgaben…
                </>
              ) : (
                "Scan starten"
              )}
            </button>
          </form>

          {/* Error */}
          {error && (
            <div
              role="alert"
              className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400"
            >
              {error}
            </div>
          )}

          {/* Results */}
          {result && (
            <section className="mt-10" aria-label="Scan-Ergebnis">
              {/* Total saving */}
              <div className="mb-6 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground">Ergebnis</h2>
                {result.totalSavingEstimate > 0 && (
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-xs text-muted">Gesamt-Ersparnis ca.</span>
                    <span className="font-mono text-lg font-semibold text-saving">
                      {result.totalSavingEstimate.toLocaleString("de-DE")} €
                    </span>
                  </div>
                )}
              </div>

              {/* Scanned items */}
              <div className="space-y-3">
                {result.items.map((item, i) => (
                  <ScannedExpenseCard key={i} item={item} />
                ))}
              </div>

              {/* Missing positions */}
              {result.missingPositions.length > 0 && (
                <div className="mt-4 rounded-lg border border-border bg-surface-raised p-4">
                  <p className="mb-2 text-xs font-medium text-muted">
                    Möglicherweise vergessene Positionen:
                  </p>
                  <ul className="space-y-1">
                    {result.missingPositions.map((pos, i) => (
                      <li key={i} className="flex items-center gap-2 text-xs text-muted">
                        <span className="h-1 w-1 shrink-0 rounded-full bg-muted" aria-hidden />
                        {pos}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Disclaimer */}
              <p className="mt-6 text-xs leading-relaxed text-muted">
                Alle Angaben ohne Gewähr. Die Ersparnis-Schätzungen basieren auf dem
                Grenzsteuersatz und sind als erste Orientierung gedacht — keine
                Steuerberatung.
              </p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
