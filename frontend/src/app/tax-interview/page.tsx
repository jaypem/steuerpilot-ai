"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import SourceChip from "@/components/chat/SourceChip";
import { useChatContext } from "@/context/ChatContext";
import {
  answerTaxInterviewQuestion,
  evaluateTaxInterview,
  fetchTaxInterview,
  startTaxInterview,
} from "@/lib/api";
import type {
  TaxInterview,
  TaxInterviewFinding,
  TaxInterviewTrafficLight,
} from "@/types/taxInterview";

// ─── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  basis: "Basisdaten & Sonderausgaben",
  arbeit: "Arbeit & Beruf",
  wohnen: "Wohnen, Haushalt & Energie",
  nebenberuf: "Nebenberuf & Ehrenamt",
  vermietung: "Vermietung & Verpachtung",
  vorsorge: "Vorsorge & Versicherungen",
  kapital: "Kapitalanlagen",
  gesundheit: "Gesundheit, Pflege & außergewöhnliche Belastungen",
};

const LIGHT_STYLES: Record<
  TaxInterviewTrafficLight,
  { pill: string; dot: string; label: string }
> = {
  green: { pill: "bg-green-500/10 text-green-400", dot: "bg-green-500", label: "Steuerchance erkennbar" },
  yellow: { pill: "bg-yellow-400/10 text-yellow-400", dot: "bg-yellow-400", label: "Belege oder Angaben nötig" },
  red: { pill: "bg-red-500/10 text-red-400", dot: "bg-red-500", label: "Kein Potenzial" },
};

// ─── Small components ─────────────────────────────────────────────────────────

function AnswerButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors ${active
          ? "border-accent bg-accent-subtle text-accent"
          : "border-border bg-surface-raised text-muted hover:border-accent hover:text-accent"
        }`}
    >
      {label}
    </button>
  );
}

function FindingCard({ finding }: { finding: TaxInterviewFinding }) {
  const style = LIGHT_STYLES[finding.trafficLight];
  const categoryLabel = CATEGORY_LABELS[finding.category] ?? finding.category;

  return (
    <div className="rounded-2xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-wide text-muted">
            {categoryLabel}
          </div>
          <h3 className="mt-1 text-sm font-semibold text-foreground">
            {finding.title}
          </h3>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span
            className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium ${style.pill}`}
          >
            <span className={`h-2 w-2 rounded-full ${style.dot}`} />
            {style.label}
          </span>
          {finding.estimatedSavingEur != null && (
            <span className="font-mono text-xs text-muted">
              ca. {finding.estimatedSavingEur.toLocaleString("de-DE")} €
            </span>
          )}
        </div>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-muted">
        {finding.explanation}
      </p>

      {finding.requiredEvidence.length > 0 && (
        <div className="mt-4">
          <div className="mb-1.5 text-[11px] uppercase tracking-wide text-muted">
            Benötigte Nachweise
          </div>
          <ul className="space-y-1 text-xs text-foreground">
            {finding.requiredEvidence.map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-0.5 text-muted">–</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {finding.sources.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {finding.sources.map((source, i) => (
            <SourceChip key={i} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main page component ──────────────────────────────────────────────────────

function TaxInterviewPageContent() {
  const { activeSessionId, taxYear, refreshSessions } = useChatContext();
  const [interview, setInterview] = useState<TaxInterview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Local answer state for number/text inputs before submission
  const [pendingAnswer, setPendingAnswer] = useState<string>("");
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  // Reset pending input whenever the question changes
  const currentQuestionId = interview?.nextQuestion?.id;
  useEffect(() => {
    setPendingAnswer("");
  }, [currentQuestionId]);

  // Load existing interview on mount / session change
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchTaxInterview(activeSessionId);
        if (!cancelled) setInterview(data);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Fehler beim Laden.");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [activeSessionId]);

  async function handleStart() {
    setIsBusy(true);
    setError(null);
    try {
      const data = await startTaxInterview(activeSessionId, taxYear);
      setInterview(data);
      await refreshSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Interview konnte nicht gestartet werden.");
    } finally {
      setIsBusy(false);
    }
  }

  async function submitAnswer(answer: boolean | number | string) {
    if (!interview?.nextQuestion) return;
    setIsBusy(true);
    setError(null);
    try {
      const updated = await answerTaxInterviewQuestion(
        activeSessionId,
        interview.nextQuestion.id,
        answer,
      );
      setInterview(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Antwort konnte nicht gespeichert werden.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleEvaluate() {
    setIsBusy(true);
    setError(null);
    try {
      const result = await evaluateTaxInterview(activeSessionId);
      setInterview(result);
      await refreshSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auswertung fehlgeschlagen.");
    } finally {
      setIsBusy(false);
    }
  }

  const answeredCount = interview ? Object.keys(interview.answers).length : 0;
  const currentCategory = interview?.nextQuestion
    ? CATEGORY_LABELS[interview.nextQuestion.category] ?? interview.nextQuestion.category
    : null;
  const totalSaving = (interview?.findings ?? []).reduce(
    (sum, f) => sum + (f.estimatedSavingEur ?? 0),
    0,
  );

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full flex-col bg-surface">
      {/* Page header */}
      <div className="border-b border-border bg-surface-raised px-4 py-3">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs text-muted">
              <Link href="/" className="hover:text-foreground">Chat</Link>
              <span>·</span>
              <span>Steuer-Interview</span>
            </div>
            <h1 className="mt-1 text-base font-semibold text-foreground">
              Proaktiver Steuer-Check
            </h1>
            <p className="mt-1 max-w-xl text-xs leading-relaxed text-muted">
              Beantworte gezielte Fragen zu deiner Steuersituation. Das Tool prüft
              danach alle 8 Kategorien mit echten Gesetzestexten und gibt dir eine
              strukturierte Übersicht deiner Steuerchancen.
            </p>
          </div>
          <span className="rounded-full bg-accent-subtle px-2 py-0.5 font-mono text-xs font-medium text-accent">
            {taxYear}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-8">
          {error && (
            <div className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="rounded-2xl border border-border bg-surface-raised px-5 py-6 text-sm text-muted">
              Lade Interview-Status...
            </div>
          ) : interview === null ? (
            // ── Phase 1: Start ──────────────────────────────────────────────
            <div className="rounded-2xl border border-border bg-surface-raised p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">
                Wie funktioniert der Steuer-Check?
              </h2>
              <ul className="mt-3 space-y-2 text-xs leading-relaxed text-muted">
                <li>· Du beantwortest Fragen zu 8 Steuerkategorien — jeweils eine nach der anderen.</li>
                <li>· Folgefragen erscheinen nur, wenn sie für deine Situation relevant sind.</li>
                <li>· Nach Abschluss wertet das System deine Antworten mit Gesetzestexten und KI aus.</li>
                <li>· Du erhältst pro Kategorie eine Einordnung mit Ampel, Erklärung und benötigten Belegen.</li>
              </ul>
              <div className="mt-6">
                <button
                  type="button"
                  onClick={() => void handleStart()}
                  disabled={isBusy}
                  className="rounded-md bg-accent px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isBusy ? "Starte..." : "Interview starten"}
                </button>
              </div>
            </div>
          ) : interview.status === "evaluated" ? (
            // ── Phase 3: Report ─────────────────────────────────────────────
            <div className="space-y-5">
              {/* Summary card */}
              <div className="rounded-2xl border border-border bg-surface-raised p-5 shadow-sm">
                <div className="text-xs uppercase tracking-wide text-muted">
                  Geschätzte Steuerersparnis
                </div>
                <div className="mt-1 font-mono text-2xl font-bold text-saving">
                  {totalSaving > 0
                    ? `ca. ${totalSaving.toLocaleString("de-DE")} €`
                    : "Keine Zahlen belastbar quantifizierbar"}
                </div>
                <p className="mt-1 text-xs text-muted">
                  Basierend auf {interview.findings?.length ?? 0} ausgewerteten Kategorien
                </p>
              </div>

              {/* Finding cards */}
              {(interview.findings ?? []).map((finding) => (
                <FindingCard key={finding.category} finding={finding} />
              ))}

              {/* Restart */}
              <div className="flex justify-start pt-2">
                <button
                  type="button"
                  onClick={() => void handleStart()}
                  disabled={isBusy}
                  className="rounded-md border border-border px-3 py-2 text-xs text-foreground transition-colors hover:bg-border disabled:opacity-50"
                >
                  Neues Interview starten
                </button>
              </div>
            </div>
          ) : (
            // ── Phase 2: Questions ──────────────────────────────────────────
            <div className="space-y-5">
              {/* Progress indicator */}
              <div className="rounded-xl border border-border bg-surface-raised px-4 py-3">
                <div className="flex items-center justify-between text-xs text-muted">
                  <span>
                    {answeredCount === 0
                      ? "Noch keine Fragen beantwortet"
                      : `${answeredCount} ${answeredCount === 1 ? "Frage" : "Fragen"} beantwortet`}
                  </span>
                  {currentCategory && (
                    <span className="text-accent">
                      {currentCategory}
                    </span>
                  )}
                </div>
                {/* Category progress dots */}
                <div className="mt-2 flex gap-1.5">
                  {Object.keys(CATEGORY_LABELS).map((cat) => {
                    const isDone =
                      interview.status === "completed" ||
                      (interview.nextQuestion !== null &&
                        interview.nextQuestion.category !== cat &&
                        Object.keys(interview.answers).some(
                          (id) => id.startsWith(cat.split(".")[0]) || id.includes(cat),
                        ));
                    const isCurrent =
                      interview.nextQuestion?.category === cat;
                    return (
                      <div
                        key={cat}
                        title={CATEGORY_LABELS[cat]}
                        className={`h-1.5 flex-1 rounded-full transition-colors ${isCurrent
                            ? "bg-accent"
                            : isDone
                              ? "bg-accent/40"
                              : "bg-border"
                          }`}
                      />
                    );
                  })}
                </div>
              </div>

              {interview.status === "completed" ? (
                // All questions answered — offer evaluation
                <div className="rounded-2xl border border-border bg-surface-raised p-6 shadow-sm">
                  <h2 className="text-sm font-semibold text-foreground">
                    Alle Fragen beantwortet
                  </h2>
                  <p className="mt-2 text-xs leading-relaxed text-muted">
                    Steuerpilot wertet jetzt deine Antworten mit echten Gesetzestexten
                    aus. Das dauert etwa 10–20 Sekunden.
                  </p>
                  <div className="mt-5 flex gap-3">
                    <button
                      type="button"
                      onClick={() => void handleEvaluate()}
                      disabled={isBusy}
                      className="rounded-md bg-accent px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isBusy ? "Wertet aus…" : "Jetzt auswerten"}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleStart()}
                      disabled={isBusy}
                      className="rounded-md border border-border px-3 py-2 text-xs text-foreground transition-colors hover:bg-border disabled:opacity-50"
                    >
                      Von vorne
                    </button>
                  </div>
                </div>
              ) : interview.nextQuestion ? (
                // Active question card
                <div className="rounded-2xl border border-border bg-surface-raised p-6 shadow-sm">
                  <p className="text-sm leading-relaxed text-foreground">
                    {interview.nextQuestion.text}
                  </p>

                  <div className="mt-5">
                    {interview.nextQuestion.answerType === "bool" && (
                      <div className="flex gap-3">
                        <AnswerButton
                          active={false}
                          label="Ja"
                          onClick={() => void submitAnswer(true)}
                        />
                        <AnswerButton
                          active={false}
                          label="Nein"
                          onClick={() => void submitAnswer(false)}
                        />
                      </div>
                    )}

                    {interview.nextQuestion.answerType === "choice" &&
                      interview.nextQuestion.options && (
                        <div className="flex flex-wrap gap-2">
                          {interview.nextQuestion.options.map((option) => (
                            <AnswerButton
                              key={option}
                              active={false}
                              label={option}
                              onClick={() => void submitAnswer(option)}
                            />
                          ))}
                        </div>
                      )}

                    {interview.nextQuestion.answerType === "number" && (
                      <div className="flex gap-2">
                        <input
                          ref={inputRef as React.RefObject<HTMLInputElement>}
                          type="number"
                          min={0}
                          value={pendingAnswer}
                          onChange={(e) => setPendingAnswer(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && pendingAnswer !== "")
                              void submitAnswer(Number(pendingAnswer));
                          }}
                          placeholder="Zahl eingeben"
                          className="w-40 rounded-xl border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={() => void submitAnswer(Number(pendingAnswer))}
                          disabled={isBusy || pendingAnswer === ""}
                          className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Weiter
                        </button>
                      </div>
                    )}

                    {interview.nextQuestion.answerType === "text" && (
                      <div className="space-y-2">
                        <textarea
                          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
                          rows={3}
                          value={pendingAnswer}
                          onChange={(e) => setPendingAnswer(e.target.value)}
                          placeholder="Freitext eingeben"
                          className="w-full rounded-xl border border-border bg-surface px-3 py-3 text-sm text-foreground focus:border-accent focus:outline-none"
                        />
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={() => void submitAnswer(pendingAnswer)}
                            disabled={isBusy || pendingAnswer.trim() === ""}
                            className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Weiter
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="mt-5 border-t border-border pt-4">
                    <button
                      type="button"
                      onClick={() => void handleStart()}
                      disabled={isBusy}
                      className="text-xs text-muted transition-colors hover:text-foreground disabled:opacity-50"
                    >
                      Von vorne starten
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TaxInterviewPage() {
  return (
    <AppShell>
      <TaxInterviewPageContent />
    </AppShell>
  );
}
