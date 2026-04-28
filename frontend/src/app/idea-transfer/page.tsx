"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import AssistantMessage from "@/components/chat/AssistantMessage";
import SourceChip from "@/components/chat/SourceChip";
import AppShell from "@/components/layout/AppShell";
import { useChatContext } from "@/context/ChatContext";
import {
  DOUBLE_TAX_SAVINGS_INFO_URL,
  DOUBLE_TAX_SAVINGS_LABEL,
  DOUBLE_TAX_SAVINGS_TOOLTIP,
} from "@/lib/doubleTaxSavings";
import {
  evaluateIdeaTransferCase,
  fetchIdeaTransferCase,
  saveIdeaTransferDraft,
} from "@/lib/api";
import {
  evaluateMockIdeaTransferCase,
  getMockIdeaTransferCase,
  saveMockIdeaTransferDraft,
} from "@/lib/mockIdeaTransfer";
import type { Message, RiskBadge } from "@/types/chat";
import type {
  IdeaTransferAnswers,
  IdeaTransferCaseKind,
  IdeaTransferEvaluationResult,
  IdeaTransferTrafficLight,
} from "@/types/ideaTransfer";

const STEPS = [
  "Falltyp",
  "Entstehung",
  "Gegenleistung",
  "Bewertung",
  "Ergebnis",
] as const;

const MOCK_DEFAULT_CASE = {
  caseKind: "own_gmbh_sale" as IdeaTransferCaseKind,
  answers: {
    ideaSummary:
      "Privat entwickelte Methodik zur automatisierten Belegerfassung fuer kleine Dienstleister.",
    originScope: "private" as const,
    connectedToJobOrBusiness: "no" as const,
    isPaidTransfer: "yes" as const,
    purchasePriceEur: 85000,
    considerationType: "cash" as const,
    buyerUsePlanAvailable: "yes" as const,
    buyerUseDescription:
      "Die eigene GmbH will die Methodik in den Kernprozess fuer die Belegvorerfassung integrieren.",
    valuationMode: "external" as const,
    documentationStatus: "complete" as const,
    familyValueAlignment: "unclear" as const,
    usefulLifeYears: 5 as const,
  } satisfies IdeaTransferAnswers,
};

const LIGHT_STYLES: Record<
  IdeaTransferTrafficLight,
  { dot: string; pill: string; label: string }
> = {
  green: {
    dot: "bg-green-500",
    pill: "bg-green-500/10 text-green-400",
    label: "Gruen",
  },
  yellow: {
    dot: "bg-yellow-400",
    pill: "bg-yellow-400/10 text-yellow-400",
    label: "Gelb",
  },
  red: {
    dot: "bg-red-500",
    pill: "bg-red-500/10 text-red-400",
    label: "Rot",
  },
};

function caseTitle(caseKind: IdeaTransferCaseKind): string {
  return caseKind === "own_gmbh_sale"
    ? "Verkauf an die eigene GmbH"
    : "Familien-Transfer";
}

function riskBadgeForTrafficLight(
  trafficLight: IdeaTransferTrafficLight,
): RiskBadge {
  if (trafficLight === "green") {
    return {
      level: "low",
      label: "Plausibel pruefbar",
      explanation:
        "Die Struktur wirkt nach den aktuellen Angaben fuer einen Vorab-Check nachvollziehbar.",
    };
  }
  if (trafficLight === "yellow") {
    return {
      level: "medium",
      label: "Nur mit Zusatzpruefung",
      explanation:
        "Bewertung, Dokumentation oder Wertgleichheit sind noch nicht vollstaendig belastbar.",
    };
  }
  return {
    level: "high",
    label: "Derzeit nicht tragfaehig",
    explanation:
      "Mindestens ein harter Blocker spricht aktuell gegen die Struktur.",
  };
}

function resultMessage(result: IdeaTransferEvaluationResult): Message {
  return {
    id: "idea-transfer-result",
    role: "assistant",
    content: result.summaryMarkdown,
    sources: result.sources,
    riskBadge: riskBadgeForTrafficLight(result.trafficLight),
    savingAmount: result.estimatedTaxBenefitMidEur ?? undefined,
    timestamp: new Date(),
  };
}

function inferStep(
  caseKind: IdeaTransferCaseKind,
  answers: IdeaTransferAnswers,
  result: IdeaTransferEvaluationResult | null,
): number {
  if (result) return 5;
  if (
    answers.valuationMode ||
    answers.documentationStatus ||
    (caseKind === "family_transfer" && answers.familyValueAlignment)
  ) {
    return 4;
  }
  if (
    answers.isPaidTransfer ||
    answers.purchasePriceEur != null ||
    answers.considerationType ||
    answers.buyerUsePlanAvailable ||
    answers.usefulLifeYears
  ) {
    return 3;
  }
  if (
    answers.ideaSummary ||
    answers.originScope ||
    answers.connectedToJobOrBusiness
  ) {
    return 2;
  }
  return 1;
}

function formatCurrency(value: number): string {
  return value.toLocaleString("de-DE");
}

function parseQueryCaseKind(value: string | null): IdeaTransferCaseKind | null {
  return value === "own_gmbh_sale" || value === "family_transfer" ? value : null;
}

function parseOriginScope(value: string | null): IdeaTransferAnswers["originScope"] {
  return value === "private" || value === "professional" || value === "unclear"
    ? value
    : null;
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

function StepShell({
  children,
  title,
  description,
}: {
  children: React.ReactNode;
  title: string;
  description: string;
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

function IdeaTransferPageContent() {
  const searchParams = useSearchParams();
  const {
    activeSessionId,
    taxYear,
    isMockMode,
    refreshSessions,
    reloadActiveSession,
  } = useChatContext();
  const [caseKind, setCaseKind] = useState<IdeaTransferCaseKind>("own_gmbh_sale");
  const [answers, setAnswers] = useState<IdeaTransferAnswers>({});
  const [result, setResult] = useState<IdeaTransferEvaluationResult | null>(null);
  const [step, setStep] = useState(1);
  const [isLoadingCase, setIsLoadingCase] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const queryKey = searchParams.toString();

  useEffect(() => {
    let cancelled = false;

    async function loadCase() {
      setIsLoadingCase(true);
      setError(null);

      const queryCaseKind = parseQueryCaseKind(searchParams.get("case_kind"));
      const queryOriginScope = parseOriginScope(searchParams.get("origin_scope"));

      try {
        const existingCase = isMockMode
          ? await getMockIdeaTransferCase(activeSessionId)
          : await fetchIdeaTransferCase(activeSessionId);

        if (cancelled) return;

        if (existingCase) {
          setCaseKind(existingCase.caseKind);
          setAnswers(existingCase.answers);
          setResult(existingCase.result ?? null);
          setStep(
            inferStep(
              existingCase.caseKind,
              existingCase.answers,
              existingCase.result ?? null,
            ),
          );
          return;
        }

        const baseAnswers = isMockMode ? MOCK_DEFAULT_CASE.answers : {};
        const nextCaseKind =
          queryCaseKind ?? (isMockMode ? MOCK_DEFAULT_CASE.caseKind : "own_gmbh_sale");
        const nextAnswers: IdeaTransferAnswers = {
          ...baseAnswers,
          ...(queryOriginScope ? { originScope: queryOriginScope } : {}),
        };

        setCaseKind(nextCaseKind);
        setAnswers(nextAnswers);
        setResult(null);
        setStep(queryCaseKind ? 2 : 1);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : `${DOUBLE_TAX_SAVINGS_LABEL}-Fall konnte nicht geladen werden.`,
        );
      } finally {
        if (!cancelled) {
          setIsLoadingCase(false);
        }
      }
    }

    void loadCase();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, isMockMode, queryKey, searchParams]);

  const updateAnswers = useCallback(
    <K extends keyof IdeaTransferAnswers>(
      key: K,
      value: IdeaTransferAnswers[K],
    ) => {
      setAnswers((prev) => ({ ...prev, [key]: value }));
      setResult(null);
    },
    [],
  );

  const persistDraft = useCallback(async () => {
    setIsSaving(true);
    setError(null);
    try {
      const storedCase = isMockMode
        ? await saveMockIdeaTransferDraft(activeSessionId, {
            caseKind,
            answers,
          })
        : await saveIdeaTransferDraft(activeSessionId, caseKind, answers);

      setCaseKind(storedCase.caseKind);
      setAnswers(storedCase.answers);
      setResult(storedCase.result ?? null);
      await refreshSessions();
      return storedCase;
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Entwurf konnte nicht gespeichert werden.",
      );
      return null;
    } finally {
      setIsSaving(false);
    }
  }, [activeSessionId, answers, caseKind, isMockMode, refreshSessions]);

  const validateStep = useCallback((): boolean => {
    if (step === 2) {
      if (!answers.ideaSummary?.trim()) {
        setError("Bitte beschreibe die Idee oder Erfindung kurz.");
        return false;
      }
      if (!answers.originScope) {
        setError("Bitte ordne ein, ob die Idee privat oder beruflich entstanden ist.");
        return false;
      }
      if (!answers.connectedToJobOrBusiness) {
        setError(
          "Bitte ordne die Naehe zu Anstellung, Arbeitgeber oder laufendem Betrieb ein.",
        );
        return false;
      }
    }

    if (step === 3) {
      if (!answers.isPaidTransfer) {
        setError("Bitte gib an, ob eine entgeltliche Uebertragung geplant ist.");
        return false;
      }
      if (!answers.considerationType) {
        setError("Bitte beschreibe die geplante Gegenleistung.");
        return false;
      }
      if (!answers.buyerUsePlanAvailable) {
        setError("Bitte gib an, ob ein Nutzungsplan beim Erwerber vorliegt.");
        return false;
      }
      if (
        answers.buyerUsePlanAvailable === "yes" &&
        !answers.buyerUseDescription?.trim()
      ) {
        setError("Bitte beschreibe kurz den geplanten Einsatz beim Erwerber.");
        return false;
      }
      if (caseKind === "own_gmbh_sale") {
        if (!answers.purchasePriceEur || answers.purchasePriceEur <= 0) {
          setError("Bitte hinterlege fuer den GmbH-Fall einen geplanten Kaufpreis.");
          return false;
        }
        if (!answers.usefulLifeYears) {
          setError("Bitte waehle eine angenommene Nutzungsdauer.");
          return false;
        }
      }
    }

    if (step === 4) {
      if (!answers.valuationMode) {
        setError("Bitte ordne den Stand der Bewertung ein.");
        return false;
      }
      if (!answers.documentationStatus) {
        setError("Bitte ordne den Stand der Dokumentation ein.");
        return false;
      }
      if (caseKind === "family_transfer" && !answers.familyValueAlignment) {
        setError(
          "Bitte schaetze ein, ob Gegenleistung und uebertragener Vorteil wertgleich sind.",
        );
        return false;
      }
    }

    setError(null);
    return true;
  }, [answers, caseKind, step]);

  const handleNext = useCallback(async () => {
    if (!validateStep()) return;
    const storedCase = await persistDraft();
    if (storedCase) {
      setStep((current) => Math.min(current + 1, 4));
    }
  }, [persistDraft, validateStep]);

  const handleEvaluate = useCallback(async () => {
    if (!validateStep()) return;

    setIsSaving(true);
    setError(null);
    try {
      const evaluatedCase = isMockMode
        ? await evaluateMockIdeaTransferCase(activeSessionId, taxYear, {
            caseKind,
            answers,
          })
        : await evaluateIdeaTransferCase(activeSessionId, taxYear, caseKind, answers);

      setCaseKind(evaluatedCase.caseKind);
      setAnswers(evaluatedCase.answers);
      setResult(evaluatedCase.result ?? null);
      setStep(5);
      await refreshSessions();
      await reloadActiveSession();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Fall konnte nicht bewertet werden.",
      );
    } finally {
      setIsSaving(false);
    }
  }, [
    activeSessionId,
    answers,
    caseKind,
    isMockMode,
    refreshSessions,
    reloadActiveSession,
    taxYear,
    validateStep,
  ]);

  const savingsBand = useMemo(() => {
    if (!result || result.estimatedTaxBenefitMidEur == null) return null;
    return {
      min: result.estimatedTaxBenefitMinEur ?? result.estimatedTaxBenefitMidEur,
      mid: result.estimatedTaxBenefitMidEur,
      max: result.estimatedTaxBenefitMaxEur ?? result.estimatedTaxBenefitMidEur,
      annual: result.annualTaxBenefitMidEur,
    };
  }, [result]);

  const displayMessage = result ? resultMessage(result) : null;

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
              <a
                href={DOUBLE_TAX_SAVINGS_INFO_URL}
                target="_blank"
                rel="noopener noreferrer"
                title={DOUBLE_TAX_SAVINGS_TOOLTIP}
                className="hover:text-foreground"
              >
                {DOUBLE_TAX_SAVINGS_LABEL}
              </a>
            </div>
            <h1 className="mt-1 text-base font-semibold text-foreground">
              {DOUBLE_TAX_SAVINGS_LABEL}
            </h1>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-muted">
              Der strukturierte Check fuer Ideen-Transfer GmbH und
              Familien-Transfer. Ausgabe als Ampel, Dokumentationsbedarf und
              Sparspanne unter Annahmen. Mehr Kontext auf{" "}
              <a
                href={DOUBLE_TAX_SAVINGS_INFO_URL}
                target="_blank"
                rel="noopener noreferrer"
                title={DOUBLE_TAX_SAVINGS_TOOLTIP}
                className="text-accent underline hover:text-accent-hover"
              >
                {DOUBLE_TAX_SAVINGS_LABEL}
              </a>
              .
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-accent-subtle px-2 py-0.5 font-mono text-xs font-medium text-accent">
              {taxYear}
            </span>
            <span
              title={DOUBLE_TAX_SAVINGS_TOOLTIP}
              className="rounded-full border border-border px-2 py-0.5 font-mono text-xs text-muted"
            >
              {caseTitle(caseKind)}
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl px-4 py-8">
          <div className="mb-6 grid gap-2 md:grid-cols-5">
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

          {isLoadingCase ? (
            <div className="rounded-2xl border border-border bg-surface-raised px-5 py-6 text-sm text-muted">
              {DOUBLE_TAX_SAVINGS_LABEL}-Fall wird geladen...
            </div>
          ) : (
            <div className="space-y-5">
              {step === 1 && (
                <StepShell
                  title="Falltyp festlegen"
                  description="Waehl den Zielpfad. Davon haengen Bewertungslogik, Sparspanne und Dokumentationshinweise ab."
                >
                  <div className="grid gap-3 md:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => setCaseKind("own_gmbh_sale")}
                      className={`rounded-xl border p-4 text-left transition-colors ${
                        caseKind === "own_gmbh_sale"
                          ? "border-accent bg-accent-subtle"
                          : "border-border bg-surface hover:border-accent"
                      }`}
                    >
                      <div className="text-sm font-medium text-foreground">
                        Verkauf an die eigene GmbH
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-muted">
                        Mit fester Sparspanne in v1, Kaufpreis, Nutzungsdauer und
                        Fremdvergleich stehen im Vordergrund.
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={() => setCaseKind("family_transfer")}
                      className={`rounded-xl border p-4 text-left transition-colors ${
                        caseKind === "family_transfer"
                          ? "border-accent bg-accent-subtle"
                          : "border-border bg-surface hover:border-accent"
                      }`}
                    >
                      <div className="text-sm font-medium text-foreground">
                        Familien-Transfer
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-muted">
                        Fokus auf Wertgleichheit, Dokumentation und Abgrenzung zur
                        freigebigen Zuwendung; ohne feste Euro-Sparzahl in v1.
                      </p>
                    </button>
                  </div>
                </StepShell>
              )}

              {step === 2 && (
                <StepShell
                  title="Entstehung und Privatbezug"
                  description="Hier trennt sich der Spezialfall am staerksten von dienstlichen oder betriebsbezogenen Konstellationen."
                >
                  <div className="space-y-5">
                    <div>
                      <label
                        htmlFor="idea-summary"
                        className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted"
                      >
                        Kurzbeschreibung der Idee
                      </label>
                      <textarea
                        id="idea-summary"
                        rows={5}
                        value={answers.ideaSummary ?? ""}
                        onChange={(e) =>
                          updateAnswers("ideaSummary", e.target.value || null)
                        }
                        placeholder="Worum geht es, wann ist die Idee entstanden und worin liegt ihr moeglicher Nutzen?"
                        className="w-full rounded-xl border border-border bg-surface px-3 py-3 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
                      />
                    </div>

                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                        Ist die Idee privat entstanden?
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <ChoiceButton
                          active={answers.originScope === "private"}
                          label="Privat"
                          onClick={() => updateAnswers("originScope", "private")}
                        />
                        <ChoiceButton
                          active={answers.originScope === "professional"}
                          label="Beruflich/Dienstlich"
                          onClick={() => updateAnswers("originScope", "professional")}
                        />
                        <ChoiceButton
                          active={answers.originScope === "unclear"}
                          label="Unklar"
                          onClick={() => updateAnswers("originScope", "unclear")}
                        />
                      </div>
                    </div>

                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                        Naehe zu Arbeitgeber oder laufendem Betrieb
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <ChoiceButton
                          active={answers.connectedToJobOrBusiness === "no"}
                          label="Keine erkennbare Naehe"
                          onClick={() =>
                            updateAnswers("connectedToJobOrBusiness", "no")
                          }
                        />
                        <ChoiceButton
                          active={answers.connectedToJobOrBusiness === "yes"}
                          label="Ja, betriebs-/jobnah"
                          onClick={() =>
                            updateAnswers("connectedToJobOrBusiness", "yes")
                          }
                        />
                        <ChoiceButton
                          active={answers.connectedToJobOrBusiness === "unclear"}
                          label="Noch unklar"
                          onClick={() =>
                            updateAnswers("connectedToJobOrBusiness", "unclear")
                          }
                        />
                      </div>
                    </div>
                  </div>
                </StepShell>
              )}

              {step === 3 && (
                <StepShell
                  title="Gegenleistung und Erwerber-Nutzung"
                  description="Hier werden Kaufpreis, entgeltliche Struktur und Nutzungsplan beim Erwerber festgehalten."
                >
                  <div className="space-y-5">
                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                        Entgeltliche Uebertragung geplant?
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <ChoiceButton
                          active={answers.isPaidTransfer === "yes"}
                          label="Ja"
                          onClick={() => updateAnswers("isPaidTransfer", "yes")}
                        />
                        <ChoiceButton
                          active={answers.isPaidTransfer === "no"}
                          label="Nein"
                          onClick={() => updateAnswers("isPaidTransfer", "no")}
                        />
                        <ChoiceButton
                          active={answers.isPaidTransfer === "unclear"}
                          label="Unklar"
                          onClick={() => updateAnswers("isPaidTransfer", "unclear")}
                        />
                      </div>
                    </div>

                    {caseKind === "own_gmbh_sale" && (
                      <div>
                        <label
                          htmlFor="purchase-price"
                          className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted"
                        >
                          Geplanter Kaufpreis in EUR
                        </label>
                        <input
                          id="purchase-price"
                          type="number"
                          min="0"
                          step="1000"
                          value={answers.purchasePriceEur ?? ""}
                          onChange={(e) =>
                            updateAnswers(
                              "purchasePriceEur",
                              e.target.value ? Number(e.target.value) : null,
                            )
                          }
                          className="w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
                          placeholder="z. B. 100000"
                        />
                      </div>
                    )}

                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                        Gegenleistung
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <ChoiceButton
                          active={answers.considerationType === "cash"}
                          label="Bargeld / Kaufpreis"
                          onClick={() => updateAnswers("considerationType", "cash")}
                        />
                        <ChoiceButton
                          active={answers.considerationType === "asset_transfer"}
                          label="Asset-Transfer"
                          onClick={() =>
                            updateAnswers("considerationType", "asset_transfer")
                          }
                        />
                        <ChoiceButton
                          active={answers.considerationType === "mixed"}
                          label="Gemischt"
                          onClick={() => updateAnswers("considerationType", "mixed")}
                        />
                        <ChoiceButton
                          active={answers.considerationType === "unclear"}
                          label="Unklar"
                          onClick={() => updateAnswers("considerationType", "unclear")}
                        />
                      </div>
                    </div>

                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                        Liegt ein Nutzungsplan beim Erwerber vor?
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <ChoiceButton
                          active={answers.buyerUsePlanAvailable === "yes"}
                          label="Ja"
                          onClick={() =>
                            updateAnswers("buyerUsePlanAvailable", "yes")
                          }
                        />
                        <ChoiceButton
                          active={answers.buyerUsePlanAvailable === "no"}
                          label="Nein"
                          onClick={() =>
                            updateAnswers("buyerUsePlanAvailable", "no")
                          }
                        />
                        <ChoiceButton
                          active={answers.buyerUsePlanAvailable === "unclear"}
                          label="Unklar"
                          onClick={() =>
                            updateAnswers("buyerUsePlanAvailable", "unclear")
                          }
                        />
                      </div>
                    </div>

                    {answers.buyerUsePlanAvailable === "yes" && (
                      <div>
                        <label
                          htmlFor="buyer-use"
                          className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted"
                        >
                          Kurzbeschreibung des Nutzungsplans
                        </label>
                        <textarea
                          id="buyer-use"
                          rows={4}
                          value={answers.buyerUseDescription ?? ""}
                          onChange={(e) =>
                            updateAnswers(
                              "buyerUseDescription",
                              e.target.value || null,
                            )
                          }
                          placeholder="Wie soll die Idee beim Erwerber konkret genutzt oder verwertet werden?"
                          className="w-full rounded-xl border border-border bg-surface px-3 py-3 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
                        />
                      </div>
                    )}

                    {caseKind === "own_gmbh_sale" && (
                      <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                          Angenommene Nutzungsdauer
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <ChoiceButton
                            active={answers.usefulLifeYears === 3}
                            label="3 Jahre"
                            onClick={() => updateAnswers("usefulLifeYears", 3)}
                          />
                          <ChoiceButton
                            active={answers.usefulLifeYears === 5}
                            label="5 Jahre"
                            onClick={() => updateAnswers("usefulLifeYears", 5)}
                          />
                          <ChoiceButton
                            active={answers.usefulLifeYears === 10}
                            label="10 Jahre"
                            onClick={() => updateAnswers("usefulLifeYears", 10)}
                          />
                          <ChoiceButton
                            active={answers.usefulLifeYears === "unclear"}
                            label="Unklar"
                            onClick={() =>
                              updateAnswers("usefulLifeYears", "unclear")
                            }
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </StepShell>
              )}

              {step === 4 && (
                <StepShell
                  title="Bewertung und Dokumentation"
                  description="Die Ampel basiert hier stark auf Bewertungsniveau, Vertragsreife und Dokumentationstiefe."
                >
                  <div className="space-y-5">
                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                        Stand der Bewertung
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <ChoiceButton
                          active={answers.valuationMode === "external"}
                          label="Extern / unabhaengig"
                          onClick={() => updateAnswers("valuationMode", "external")}
                        />
                        <ChoiceButton
                          active={answers.valuationMode === "internal"}
                          label="Nur intern"
                          onClick={() => updateAnswers("valuationMode", "internal")}
                        />
                        <ChoiceButton
                          active={answers.valuationMode === "none"}
                          label="Noch keine Bewertung"
                          onClick={() => updateAnswers("valuationMode", "none")}
                        />
                        <ChoiceButton
                          active={answers.valuationMode === "unclear"}
                          label="Unklar"
                          onClick={() => updateAnswers("valuationMode", "unclear")}
                        />
                      </div>
                    </div>

                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                        Stand der Dokumentation
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <ChoiceButton
                          active={answers.documentationStatus === "complete"}
                          label="Weitgehend vollstaendig"
                          onClick={() =>
                            updateAnswers("documentationStatus", "complete")
                          }
                        />
                        <ChoiceButton
                          active={answers.documentationStatus === "partial"}
                          label="Teilweise"
                          onClick={() =>
                            updateAnswers("documentationStatus", "partial")
                          }
                        />
                        <ChoiceButton
                          active={answers.documentationStatus === "none"}
                          label="Kaum vorhanden"
                          onClick={() => updateAnswers("documentationStatus", "none")}
                        />
                        <ChoiceButton
                          active={answers.documentationStatus === "unclear"}
                          label="Unklar"
                          onClick={() =>
                            updateAnswers("documentationStatus", "unclear")
                          }
                        />
                      </div>
                    </div>

                    {caseKind === "family_transfer" && (
                      <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                          Wertgleichheit im Familienfall
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <ChoiceButton
                            active={answers.familyValueAlignment === "yes"}
                            label="Plausibel wertgleich"
                            onClick={() =>
                              updateAnswers("familyValueAlignment", "yes")
                            }
                          />
                          <ChoiceButton
                            active={answers.familyValueAlignment === "no"}
                            label="Eher nicht wertgleich"
                            onClick={() =>
                              updateAnswers("familyValueAlignment", "no")
                            }
                          />
                          <ChoiceButton
                            active={answers.familyValueAlignment === "unclear"}
                            label="Noch offen"
                            onClick={() =>
                              updateAnswers("familyValueAlignment", "unclear")
                            }
                          />
                        </div>
                      </div>
                    )}

                    <div className="rounded-xl border border-border bg-surface px-4 py-3 text-xs leading-relaxed text-muted">
                      Hinweis: Ein Insichgeschaeft nach § 181 BGB ist hier nicht
                      Teil des RAG-Scopes, sollte aber im GmbH-Fall in Vertrag und
                      Prozess gesondert beachtet werden.
                    </div>
                  </div>
                </StepShell>
              )}

              {step === 5 && result && displayMessage && (
                <div className="space-y-5">
                  <StepShell
                    title="Ergebnis"
                    description="Die Ampel wird deterministisch aus den erfassten Prueffeldern abgeleitet und mit Quellen sowie naechsten Schritten angereichert."
                  >
                    <div className="space-y-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium ${
                            LIGHT_STYLES[result.trafficLight].pill
                          }`}
                        >
                          <span
                            className={`h-2 w-2 rounded-full ${
                              LIGHT_STYLES[result.trafficLight].dot
                            }`}
                          />
                          Ampel: {LIGHT_STYLES[result.trafficLight].label}
                        </span>
                        {savingsBand ? (
                          <span className="rounded-full bg-saving-subtle px-2.5 py-1 text-xs font-medium text-saving">
                            Mitte ca. {formatCurrency(savingsBand.mid)} EUR
                          </span>
                        ) : (
                          <span className="rounded-full border border-border px-2.5 py-1 text-xs text-muted">
                            Keine feste Euro-Sparspanne in v1
                          </span>
                        )}
                      </div>

                      <AssistantMessage message={displayMessage} />
                    </div>
                  </StepShell>

                  {savingsBand && (
                    <div className="grid gap-3 md:grid-cols-4">
                      <div className="rounded-xl border border-border bg-surface-raised p-4">
                        <div className="text-xs uppercase tracking-wide text-muted">
                          Minimum
                        </div>
                        <div className="mt-1 text-lg font-semibold text-foreground">
                          {formatCurrency(savingsBand.min)} EUR
                        </div>
                      </div>
                      <div className="rounded-xl border border-border bg-surface-raised p-4">
                        <div className="text-xs uppercase tracking-wide text-muted">
                          Mitte
                        </div>
                        <div className="mt-1 text-lg font-semibold text-saving">
                          {formatCurrency(savingsBand.mid)} EUR
                        </div>
                      </div>
                      <div className="rounded-xl border border-border bg-surface-raised p-4">
                        <div className="text-xs uppercase tracking-wide text-muted">
                          Maximum
                        </div>
                        <div className="mt-1 text-lg font-semibold text-foreground">
                          {formatCurrency(savingsBand.max)} EUR
                        </div>
                      </div>
                      <div className="rounded-xl border border-border bg-surface-raised p-4">
                        <div className="text-xs uppercase tracking-wide text-muted">
                          Jaehrliche Wirkung
                        </div>
                        <div className="mt-1 text-lg font-semibold text-foreground">
                          {savingsBand.annual != null
                            ? `${formatCurrency(savingsBand.annual)} EUR`
                            : "-"}
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
                    <div className="space-y-5">
                      <StepShell
                        title="Pruefdimensionen"
                        description="Jede Dimension wird separat klassifiziert und in die Gesamtampel eingerechnet."
                      >
                        <div className="space-y-3">
                          {result.dimensions.map((dimension) => (
                            <div
                              key={dimension.id}
                              className="rounded-xl border border-border bg-surface px-4 py-3"
                            >
                              <div className="flex items-center justify-between gap-3">
                                <div className="text-sm font-medium text-foreground">
                                  {dimension.title}
                                </div>
                                <span
                                  className={`inline-flex items-center gap-2 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                                    LIGHT_STYLES[dimension.trafficLight].pill
                                  }`}
                                >
                                  <span
                                    className={`h-2 w-2 rounded-full ${
                                      LIGHT_STYLES[dimension.trafficLight].dot
                                    }`}
                                  />
                                  {LIGHT_STYLES[dimension.trafficLight].label}
                                </span>
                              </div>
                              <p className="mt-2 text-xs leading-relaxed text-muted">
                                {dimension.summary}
                              </p>
                            </div>
                          ))}
                        </div>
                      </StepShell>

                      {result.sources.length > 0 && (
                        <StepShell
                          title="Quellen"
                          description="Diese Rechtsquellen wurden fuer die strukturierte Einordnung herangezogen."
                        >
                          <div className="flex flex-wrap gap-1.5">
                            {result.sources.map((source, index) => (
                              <SourceChip key={`${source.law}-${index}`} source={source} />
                            ))}
                          </div>
                        </StepShell>
                      )}
                    </div>

                    <div className="space-y-5">
                      <StepShell
                        title="Dokumentenbedarf"
                        description="Diese Unterlagen solltest du fuer die fachliche Validierung vorbereiten."
                      >
                        <ul className="space-y-2 text-sm text-foreground">
                          {result.requiredDocuments.map((item) => (
                            <li key={item} className="rounded-lg bg-surface px-3 py-2">
                              {item}
                            </li>
                          ))}
                        </ul>
                      </StepShell>

                      <StepShell
                        title="Naechste Schritte"
                        description="Die Engine gibt keine pauschale Zusage, sondern priorisiert die naechsten Arbeitspunkte."
                      >
                        <ul className="space-y-2 text-sm text-foreground">
                          {result.nextActions.map((item) => (
                            <li key={item} className="rounded-lg bg-surface px-3 py-2">
                              {item}
                            </li>
                          ))}
                        </ul>
                      </StepShell>

                      {result.assumptions.length > 0 && (
                        <StepShell
                          title="Annahmen"
                          description="Diese Annahmen fliessen direkt in die Zahlen oder die Ampel ein."
                        >
                          <ul className="space-y-2 text-sm text-foreground">
                            {result.assumptions.map((item) => (
                              <li key={item} className="rounded-lg bg-surface px-3 py-2">
                                {item}
                              </li>
                            ))}
                          </ul>
                        </StepShell>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-xs text-muted">
                  Session: <span className="font-mono">{activeSessionId}</span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {step > 1 && step < 5 && (
                    <button
                      type="button"
                      onClick={() => setStep((current) => Math.max(current - 1, 1))}
                      className="rounded-md border border-border px-3 py-2 text-xs text-foreground transition-colors hover:bg-border"
                    >
                      Zurueck
                    </button>
                  )}

                  {step === 1 && (
                    <button
                      type="button"
                      onClick={handleNext}
                      disabled={isSaving}
                      className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Weiter zu Entstehung
                    </button>
                  )}

                  {step > 1 && step < 4 && (
                    <button
                      type="button"
                      onClick={handleNext}
                      disabled={isSaving}
                      className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Speichern und weiter
                    </button>
                  )}

                  {step === 4 && (
                    <>
                      <button
                        type="button"
                        onClick={persistDraft}
                        disabled={isSaving}
                        className="rounded-md border border-border px-3 py-2 text-xs text-foreground transition-colors hover:bg-border disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Entwurf speichern
                      </button>
                      <button
                        type="button"
                        onClick={handleEvaluate}
                        disabled={isSaving}
                        className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isSaving ? "Bewerte..." : "Ampel berechnen"}
                      </button>
                    </>
                  )}

                  {step === 5 && (
                    <>
                      <button
                        type="button"
                        onClick={() => setStep(4)}
                        className="rounded-md border border-border px-3 py-2 text-xs text-foreground transition-colors hover:bg-border"
                      >
                        Angaben bearbeiten
                      </button>
                      <button
                        type="button"
                        onClick={handleEvaluate}
                        disabled={isSaving}
                        className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isSaving ? "Berechne neu..." : "Neu bewerten"}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function IdeaTransferPage() {
  return (
    <AppShell>
      <Suspense
        fallback={
          <div className="flex h-full items-center justify-center bg-surface px-4 text-sm text-muted">
            {DOUBLE_TAX_SAVINGS_LABEL}-Check wird geladen...
          </div>
        }
      >
        <IdeaTransferPageContent />
      </Suspense>
    </AppShell>
  );
}
