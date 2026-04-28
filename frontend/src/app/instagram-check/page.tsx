"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import { useChatContext } from "@/context/ChatContext";
import {
  analyzeInstagramCheck,
  evaluateInstagramCheck,
  fetchInstagramCheck,
  saveInstagramCheck,
} from "@/lib/api";
import {
  analyzeMockInstagramCheck,
  evaluateMockInstagramCheck,
  fetchMockInstagramCheck,
  saveMockInstagramCheck,
} from "@/lib/mockInstagramCheck";
import type {
  InstagramClaim,
  InstagramPostCheck,
  InstagramTrafficLight,
} from "@/types/instagramCheck";

const STEPS = ["Upload", "Tipps prüfen", "Rückfragen", "Ergebnis"] as const;

const LIGHT_STYLES: Record<
  InstagramTrafficLight,
  { pill: string; dot: string; label: string }
> = {
  green: {
    pill: "bg-green-500/10 text-green-400",
    dot: "bg-green-500",
    label: "Übernehmbar",
  },
  yellow: {
    pill: "bg-yellow-400/10 text-yellow-400",
    dot: "bg-yellow-400",
    label: "Erst mit Zusatzangaben",
  },
  red: {
    pill: "bg-red-500/10 text-red-400",
    dot: "bg-red-500",
    label: "Nicht tragfähig",
  },
};

function inferStep(check: InstagramPostCheck | null): number {
  if (!check) return 1;
  if (check.status === "evaluated") return 4;
  const hasAnswers = check.claims.some((claim) =>
    claim.followUpQuestions.some((question) => question.answer?.trim()),
  );
  return hasAnswers ? 3 : 2;
}

function StepShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        <p className="mt-1 text-xs leading-relaxed text-muted">{description}</p>
      </div>
      {children}
    </section>
  );
}

function ChoiceButton({
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
      className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
        active
          ? "border-accent bg-accent-subtle text-accent"
          : "border-border bg-surface-raised text-muted hover:border-accent hover:text-accent"
      }`}
    >
      {label}
    </button>
  );
}

function InstagramCheckPageContent() {
  const {
    activeSessionId,
    taxYear,
    isMockMode,
    refreshSessions,
    reloadActiveSession,
    taxPrepItems,
    refreshTaxPrepItems,
  } = useChatContext();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [check, setCheck] = useState<InstagramPostCheck | null>(null);
  const [step, setStep] = useState(1);
  const [isBusy, setIsBusy] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadCheck() {
      setIsLoading(true);
      setError(null);
      try {
        const nextCheck = isMockMode
          ? await fetchMockInstagramCheck(activeSessionId)
          : await fetchInstagramCheck(activeSessionId);
        if (cancelled) return;
        setCheck(nextCheck);
        setStep(inferStep(nextCheck));
        await refreshTaxPrepItems();
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Instagram-Check konnte nicht geladen werden.",
        );
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadCheck();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, isMockMode, refreshTaxPrepItems]);

  const activeClaims = useMemo(
    () => (check?.claims ?? []).filter((claim) => claim.status === "active"),
    [check],
  );
  const greenTips = useMemo(
    () =>
      (check?.evaluatedTips ?? []).filter((tip) => tip.trafficLight === "green"),
    [check],
  );

  function updateClaim(
    claimId: string,
    updater: (claim: InstagramClaim) => InstagramClaim,
    options?: { preserveEvaluation?: boolean },
  ) {
    setCheck((current) => {
      if (!current) return current;
      const preserveEvaluation = options?.preserveEvaluation ?? false;
      return {
        ...current,
        status: preserveEvaluation ? current.status : "draft",
        evaluatedTips: preserveEvaluation ? current.evaluatedTips : null,
        claims: current.claims.map((claim) =>
          claim.id === claimId ? updater(claim) : claim,
        ),
      };
    });
  }

  async function handleAnalyze() {
    if (selectedFiles.length === 0) {
      setError("Bitte lade mindestens einen Screenshot hoch.");
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const nextCheck = isMockMode
        ? await analyzeMockInstagramCheck(activeSessionId, selectedFiles)
        : await analyzeInstagramCheck(activeSessionId, taxYear, selectedFiles);
      setCheck(nextCheck);
      setStep(2);
      await refreshSessions();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Bilder konnten nicht analysiert werden.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function persistDraft(nextStep?: number) {
    if (!check) return;
    setIsBusy(true);
    setError(null);
    try {
      const saved = isMockMode
        ? await saveMockInstagramCheck(activeSessionId, { claims: check.claims })
        : await saveInstagramCheck(activeSessionId, { claims: check.claims });
      setCheck(saved);
      if (nextStep) {
        setStep(nextStep);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Instagram-Check konnte nicht gespeichert werden.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function handleEvaluate() {
    if (!check) return;
    setIsBusy(true);
    setError(null);
    try {
      const evaluated = isMockMode
        ? await evaluateMockInstagramCheck(activeSessionId)
        : await evaluateInstagramCheck(activeSessionId, taxYear);
      setCheck(evaluated);
      setStep(4);
      await refreshSessions();
      await refreshTaxPrepItems();
      await reloadActiveSession();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Bewertung des Instagram-Checks fehlgeschlagen.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function handleAdoptSelected() {
    if (!check) return;
    const hasSelectedGreen = check.claims.some(
      (claim) =>
        claim.selectedForImport &&
        check.evaluatedTips?.some(
          (tip) => tip.claimId === claim.id && tip.trafficLight === "green",
        ),
    );
    if (!hasSelectedGreen) {
      setError("Bitte markiere mindestens einen grünen Tipp zur Übernahme.");
      return;
    }
    await persistDraft();
    await handleEvaluate();
  }

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="border-b border-border bg-surface-raised px-4 py-3">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs text-muted">
              <Link href="/" className="hover:text-foreground">
                Chat
              </Link>
              <span>·</span>
              <span>Instagram-Check</span>
            </div>
            <h1 className="mt-1 text-base font-semibold text-foreground">
              Instagram-Post-Check
            </h1>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-muted">
              Lade Screenshots von Instagram-Posts hoch. Das Tool extrahiert
              Steuertipps, prüft deren Nutzbarkeit für deinen Fall und übernimmt
              nur bestätigte, tragfähige Chancen in die Vorbereitung.
            </p>
          </div>
          <span className="rounded-full bg-accent-subtle px-2 py-0.5 font-mono text-xs font-medium text-accent">
            {taxYear}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl px-4 py-8">
          <div className="mb-6 grid gap-2 md:grid-cols-4">
            {STEPS.map((label, index) => {
              const stepNumber = index + 1;
              const isActive = step === stepNumber;
              const isDone = step > stepNumber;
              return (
                <div
                  key={label}
                  className={`rounded-xl border px-3 py-3 ${
                    isActive
                      ? "border-accent bg-accent-subtle"
                      : isDone
                        ? "border-border bg-surface-raised"
                        : "border-border bg-surface"
                  }`}
                >
                  <div className="text-[11px] uppercase tracking-wide text-muted">
                    Schritt {stepNumber}
                  </div>
                  <div className="mt-1 text-sm font-medium text-foreground">
                    {label}
                  </div>
                </div>
              );
            })}
          </div>

          {error && (
            <div className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="rounded-2xl border border-border bg-surface-raised px-5 py-6 text-sm text-muted">
              Instagram-Check wird geladen...
            </div>
          ) : (
            <div className="space-y-5">
              {step === 1 && (
                <StepShell
                  title="Screenshots hochladen"
                  description="Lade einen oder mehrere Screenshots eines Instagram-Posts hoch. V1 unterstützt nur manuelle Bilder, keine URLs oder automatische Caption-Imports."
                >
                  <div className="space-y-4">
                    <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-surface px-6 py-10 text-center transition-colors hover:border-accent">
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        multiple
                        className="hidden"
                        onChange={(event) =>
                          setSelectedFiles(Array.from(event.target.files ?? []))
                        }
                      />
                      <span className="text-sm font-medium text-foreground">
                        Screenshots auswählen
                      </span>
                      <span className="mt-1 text-xs text-muted">
                        PNG, JPG oder WEBP · mehrere Bilder für Carousels möglich
                      </span>
                    </label>

                    {selectedFiles.length > 0 && (
                      <ul className="rounded-xl border border-border bg-surface p-4 text-sm text-foreground">
                        {selectedFiles.map((file) => (
                          <li key={`${file.name}-${file.size}`} className="py-1">
                            {file.name}
                          </li>
                        ))}
                      </ul>
                    )}

                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={handleAnalyze}
                        disabled={isBusy}
                        className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isBusy ? "Analysiere..." : "Bilder analysieren"}
                      </button>
                    </div>
                  </div>
                </StepShell>
              )}

              {step === 2 && check && (
                <StepShell
                  title="Extrahierte Tipps prüfen"
                  description="Prüfe die atomar extrahierten Tipps, passe Formulierungen an und entferne unbrauchbare Claims."
                >
                  <div className="space-y-4">
                    {check.claims.map((claim, index) => (
                      <div
                        key={claim.id}
                        className="rounded-xl border border-border bg-surface p-4"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div className="text-sm font-medium text-foreground">
                            Tipp {index + 1}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <ChoiceButton
                              active={claim.status === "active"}
                              label="Aktiv"
                              onClick={() =>
                                updateClaim(claim.id, (current) => ({
                                  ...current,
                                  status: "active",
                                }))
                              }
                            />
                            <ChoiceButton
                              active={claim.status === "removed"}
                              label="Entfernen"
                              onClick={() =>
                                updateClaim(claim.id, (current) => ({
                                  ...current,
                                  status: "removed",
                                }))
                              }
                            />
                          </div>
                        </div>
                        <textarea
                          rows={3}
                          value={claim.editedText}
                          onChange={(event) =>
                            updateClaim(claim.id, (current) => ({
                              ...current,
                              editedText: event.target.value,
                            }))
                          }
                          className="mt-3 w-full rounded-xl border border-border bg-surface-raised px-3 py-3 text-sm text-foreground focus:border-accent focus:outline-none"
                        />
                      </div>
                    ))}

                    <div className="flex justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => setStep(1)}
                        className="rounded-md border border-border px-3 py-2 text-xs text-foreground transition-colors hover:bg-border"
                      >
                        Zurück
                      </button>
                      <button
                        type="button"
                        onClick={() => void persistDraft(3)}
                        disabled={isBusy}
                        className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Speichern und weiter
                      </button>
                    </div>
                  </div>
                </StepShell>
              )}

              {step === 3 && check && (
                <StepShell
                  title="Gezielte Rückfragen beantworten"
                  description="Beantworte pro aktivem Tipp nur die Rückfragen, die für die konkrete Anwendbarkeit und die spätere Übernahme nötig sind."
                >
                  <div className="space-y-4">
                    {activeClaims.map((claim) => (
                      <div
                        key={claim.id}
                        className="rounded-xl border border-border bg-surface p-4"
                      >
                        <div className="text-sm font-medium text-foreground">
                          {claim.editedText}
                        </div>
                        <div className="mt-4 space-y-4">
                          {claim.followUpQuestions.map((question) => (
                            <div key={question.id}>
                              <label className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted">
                                {question.prompt}
                              </label>
                              <textarea
                                rows={3}
                                value={question.answer ?? ""}
                                onChange={(event) =>
                                  updateClaim(claim.id, (current) => ({
                                    ...current,
                                    followUpQuestions: current.followUpQuestions.map((item) =>
                                      item.id === question.id
                                        ? { ...item, answer: event.target.value }
                                        : item,
                                    ),
                                  }))
                                }
                                className="w-full rounded-xl border border-border bg-surface-raised px-3 py-3 text-sm text-foreground focus:border-accent focus:outline-none"
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}

                    <div className="flex justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => setStep(2)}
                        className="rounded-md border border-border px-3 py-2 text-xs text-foreground transition-colors hover:bg-border"
                      >
                        Zurück
                      </button>
                      <button
                        type="button"
                        onClick={async () => {
                          await persistDraft();
                          await handleEvaluate();
                        }}
                        disabled={isBusy}
                        className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isBusy ? "Bewerte..." : "Tipps fachlich prüfen"}
                      </button>
                    </div>
                  </div>
                </StepShell>
              )}

              {step === 4 && check && (
                <div className="space-y-5">
                  <StepShell
                    title="Ergebnis und Übernahme"
                    description="Nur grüne Tipps können in die Vorbereitung übernommen werden. Gelbe und rote Tipps bleiben als Einordnung sichtbar."
                  >
                    <div className="space-y-4">
                      {(check.evaluatedTips ?? []).map((tip) => {
                        const style = LIGHT_STYLES[tip.trafficLight];
                        const claim = check.claims.find((item) => item.id === tip.claimId);
                        return (
                          <div
                            key={tip.claimId}
                            className="rounded-xl border border-border bg-surface p-4"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <div className="text-sm font-medium text-foreground">
                                  {tip.title}
                                </div>
                                <p className="mt-2 text-xs leading-relaxed text-muted">
                                  {tip.explanation}
                                </p>
                              </div>
                              <div className="flex flex-col items-end gap-2">
                                <span
                                  className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium ${style.pill}`}
                                >
                                  <span className={`h-2 w-2 rounded-full ${style.dot}`} />
                                  {style.label}
                                </span>
                                <span className="font-mono text-xs text-muted">
                                  {tip.estimatedSavingEur != null
                                    ? `${tip.estimatedSavingEur.toLocaleString("de-DE")} €`
                                    : "keine Zahl"}
                                </span>
                              </div>
                            </div>

                            {tip.requiredEvidence.length > 0 && (
                              <div className="mt-3">
                                <div className="text-[11px] uppercase tracking-wide text-muted">
                                  Benötigte Nachweise
                                </div>
                                <ul className="mt-2 space-y-1 text-xs text-foreground">
                                  {tip.requiredEvidence.map((item) => (
                                    <li key={item}>{item}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {tip.trafficLight === "green" && claim && (
                              <label className="mt-4 flex cursor-pointer items-center gap-2 text-xs text-foreground">
                                <input
                                  type="checkbox"
                                  checked={claim.selectedForImport}
                                  onChange={(event) =>
                                    updateClaim(claim.id, (current) => ({
                                      ...current,
                                      selectedForImport: event.target.checked,
                                    }), { preserveEvaluation: true })
                                  }
                                />
                                In die Steuererklärungsvorbereitung übernehmen
                              </label>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </StepShell>

                  {taxPrepItems.length > 0 && (
                    <StepShell
                      title="Bereits übernommene Steuerchancen"
                      description="Diese Tipps sind in der aktiven Session bereits bestätigt gespeichert."
                    >
                      <ul className="space-y-2">
                        {taxPrepItems.map((item) => (
                          <li
                            key={item.id}
                            className="rounded-xl border border-border bg-surface px-4 py-3"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <div className="text-sm font-medium text-foreground">
                                  {item.title}
                                </div>
                                <p className="mt-1 text-xs leading-relaxed text-muted">
                                  {item.summary}
                                </p>
                              </div>
                              <span className="font-mono text-xs text-muted">
                                {item.estimatedSavingEur != null
                                  ? `${item.estimatedSavingEur.toLocaleString("de-DE")} €`
                                  : "—"}
                              </span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </StepShell>
                  )}

                  <div className="flex justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => setStep(3)}
                      className="rounded-md border border-border px-3 py-2 text-xs text-foreground transition-colors hover:bg-border"
                    >
                      Antworten anpassen
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleAdoptSelected()}
                      disabled={isBusy || greenTips.length === 0}
                      className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isBusy ? "Übernehme..." : "Ausgewählte Tipps übernehmen"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function InstagramCheckPage() {
  return (
    <AppShell>
      <InstagramCheckPageContent />
    </AppShell>
  );
}
