import type {
  IdeaTransferAnswers,
  IdeaTransferCase,
  IdeaTransferCaseKind,
  IdeaTransferDraftPayload,
  IdeaTransferEvaluationResult,
  IdeaTransferTrafficLight,
} from "@/types/ideaTransfer";

const mockStore = new Map<string, IdeaTransferCase>();

function now() {
  return new Date();
}

function cloneCase(value: IdeaTransferCase): IdeaTransferCase {
  return {
    ...value,
    answers: { ...value.answers },
    result: value.result
      ? {
          ...value.result,
          dimensions: value.result.dimensions.map((dimension) => ({ ...dimension })),
          requiredDocuments: [...value.result.requiredDocuments],
          nextActions: [...value.result.nextActions],
          sources: value.result.sources.map((source) => ({ ...source })),
          assumptions: [...value.result.assumptions],
        }
      : value.result,
    updatedAt: new Date(value.updatedAt),
  };
}

function evaluateMockCase(
  caseKind: IdeaTransferCaseKind,
  answers: IdeaTransferAnswers,
): IdeaTransferEvaluationResult {
  const isHardBlocker =
    answers.originScope === "professional" ||
    answers.connectedToJobOrBusiness === "yes" ||
    answers.isPaidTransfer === "no" ||
    answers.buyerUsePlanAvailable === "no";

  const hasUncertainty =
    answers.originScope !== "private" ||
    answers.documentationStatus !== "complete" ||
    answers.valuationMode !== "external" ||
    (caseKind === "family_transfer" && answers.familyValueAlignment !== "yes");

  const trafficLight: IdeaTransferTrafficLight = isHardBlocker
    ? "red"
    : hasUncertainty
      ? "yellow"
      : "green";

  const purchasePrice = answers.purchasePriceEur ?? 0;
  const usefulLifeYears =
    answers.usefulLifeYears && answers.usefulLifeYears !== "unclear"
      ? answers.usefulLifeYears
      : 10;

  const estimatedMin =
    caseKind === "own_gmbh_sale" && purchasePrice > 0 ? Math.round(purchasePrice * 0.25) : null;
  const estimatedMid =
    caseKind === "own_gmbh_sale" && purchasePrice > 0 ? Math.round(purchasePrice * 0.3) : null;
  const estimatedMax =
    caseKind === "own_gmbh_sale" && purchasePrice > 0 ? Math.round(purchasePrice * 0.35) : null;
  const annualMid =
    estimatedMid != null ? Math.round(estimatedMid / usefulLifeYears) : null;

  return {
    trafficLight,
    headline:
      trafficLight === "green"
        ? "Der Mock-Fall wirkt aktuell grundsaetzlich pruefbar."
        : trafficLight === "yellow"
          ? "Der Mock-Fall braucht noch zusaetzliche Pruefung."
          : "Der Mock-Fall ist nach den aktuellen Angaben nicht tragfaehig.",
    summaryMarkdown:
      trafficLight === "green"
        ? "## Strukturierter Mock-Fall\n\nDie aktuelle Kombination aus privater Entstehung, Dokumentation und Bewertung wirkt fuer einen Vorab-Check stimmig."
        : trafficLight === "yellow"
          ? "## Strukturierter Mock-Fall\n\nDer Mock-Fall zeigt Potenzial, hat aber noch offene Bewertungs- oder Dokumentationspunkte."
          : "## Strukturierter Mock-Fall\n\nMindestens ein harter Blocker spricht aktuell gegen die Struktur.",
    estimatedTaxBenefitMinEur: estimatedMin,
    estimatedTaxBenefitMidEur: estimatedMid,
    estimatedTaxBenefitMaxEur: estimatedMax,
    annualTaxBenefitMidEur: annualMid,
    dimensions: [
      {
        id: "private_origin",
        title: "Private Entstehung",
        trafficLight: answers.originScope === "private" ? "green" : answers.originScope === "professional" ? "red" : "yellow",
        summary: "Mock-Bewertung zur Entstehung der Idee.",
      },
      {
        id: "employment_proximity",
        title: "Naehe zu Beschaeftigung/Betrieb",
        trafficLight: answers.connectedToJobOrBusiness === "no" ? "green" : answers.connectedToJobOrBusiness === "yes" ? "red" : "yellow",
        summary: "Mock-Bewertung zur Abgrenzung zum beruflichen Umfeld.",
      },
      {
        id: "transferability",
        title: "Uebertragbarkeit und Dokumentation",
        trafficLight: answers.documentationStatus === "complete" ? "green" : answers.documentationStatus === "none" ? "red" : "yellow",
        summary: "Mock-Bewertung zur Konkretisierung der Idee.",
      },
      {
        id: "valuation",
        title: "Bewertung und Fremdvergleich",
        trafficLight: answers.valuationMode === "external" ? "green" : answers.valuationMode === "none" ? "red" : "yellow",
        summary: "Mock-Bewertung zur Bewertungsunterlage.",
      },
      {
        id: "acquirer_use_plan",
        title: "Nutzungsplan beim Erwerber",
        trafficLight: answers.buyerUsePlanAvailable === "yes" ? "green" : answers.buyerUsePlanAvailable === "no" ? "red" : "yellow",
        summary: "Mock-Bewertung zum geplanten Einsatz beim Erwerber.",
      },
      {
        id: "transfer_tax",
        title: "Transfer-/Schenkungsteuerrelevanz",
        trafficLight:
          caseKind === "family_transfer"
            ? answers.familyValueAlignment === "yes"
              ? "green"
              : answers.familyValueAlignment === "no"
                ? "red"
                : "yellow"
            : answers.isPaidTransfer === "yes"
              ? "green"
              : answers.isPaidTransfer === "no"
                ? "red"
                : "yellow",
        summary: "Mock-Bewertung zur Wertgleichheit bzw. entgeltlichen Struktur.",
      },
    ],
    requiredDocuments: [
      "Beschreibung der Idee",
      "Uebertragungsvertrag",
      "Bewertungsunterlage",
    ],
    nextActions: [
      "Mock-Fall mit Steuerberater gegenpruefen.",
      "Dokumentation ergaenzen, bevor echte Werte angesetzt werden.",
    ],
    sources: [
      {
        law: "KStG",
        paragraph: "§ 8",
        section: "",
        text: "Mock-Hinweis auf den Fremdvergleich im GmbH-Kontext.",
      },
      {
        law: caseKind === "family_transfer" ? "ErbStG" : "EStG",
        paragraph: caseKind === "family_transfer" ? "§ 7" : "§ 5",
        section: "",
        text: "Mock-Hinweis fuer den strukturierten Spezialfall.",
      },
    ],
    assumptions:
      caseKind === "own_gmbh_sale" && answers.usefulLifeYears === "unclear"
        ? ["Im Mock wurde fuer die Jahreswirkung mit 10 Jahren gerechnet."]
        : [],
  };
}

export async function getMockIdeaTransferCase(sessionId: string): Promise<IdeaTransferCase | null> {
  return mockStore.has(sessionId) ? cloneCase(mockStore.get(sessionId)!) : null;
}

export async function saveMockIdeaTransferDraft(
  sessionId: string,
  payload: IdeaTransferDraftPayload,
): Promise<IdeaTransferCase> {
  const nextCase: IdeaTransferCase = {
    sessionId,
    caseKind: payload.caseKind,
    status: "draft",
    answers: { ...payload.answers },
    result: null,
    updatedAt: now(),
  };
  mockStore.set(sessionId, nextCase);
  return cloneCase(nextCase);
}

export async function evaluateMockIdeaTransferCase(
  sessionId: string,
  taxYear: number,
  payload: IdeaTransferDraftPayload,
): Promise<IdeaTransferCase> {
  void taxYear;
  const result = evaluateMockCase(payload.caseKind, payload.answers);
  const nextCase: IdeaTransferCase = {
    sessionId,
    caseKind: payload.caseKind,
    status: "completed",
    answers: { ...payload.answers },
    result,
    updatedAt: now(),
  };
  mockStore.set(sessionId, nextCase);
  return cloneCase(nextCase);
}
