import type { Message, RiskBadge, Source } from "@/types/chat";
import type {
  InstagramCheckSavePayload,
  InstagramClaim,
  InstagramEvaluatedTip,
  InstagramPostCheck,
  TaxPrepItem,
} from "@/types/instagramCheck";
import type {
  IdeaTransferAnswers,
  IdeaTransferCase,
  IdeaTransferCaseKind,
  IdeaTransferEvaluationResult,
} from "@/types/ideaTransfer";
import type { Session } from "@/types/session";
import type { ScanResult } from "@/types/scan";
import { parseSSEStream } from "./sseParser";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Backend payload types ────────────────────────────────────────────────────

interface ChatPayload {
  message: string;
  session_id?: string;
  tax_year?: number;
}

export type StreamChunk =
  | { type: "text"; content: string }
  | {
      type: "source";
      law: string;
      paragraph: string;
      section: string;
      text: string;
      url?: string | null;
    }
  | {
      type: "risk_badge";
      level: "low" | "medium" | "high";
      label: string;
      explanation: string;
    }
  | { type: "saving"; amount: number }
  | { type: "status"; label: string }
  | { type: "done" }
  | { type: "error"; message: string };

interface APISession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  total_saving: number;
}

interface APIMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources: Array<Source> | null;
  risk_badge: RiskBadge | null;
  saving_amount: number | null;
  created_at: string;
}

interface APISessionDetail extends APISession {
  messages: APIMessage[];
}

interface APIIdeaTransferDimension {
  id: IdeaTransferEvaluationResult["dimensions"][number]["id"];
  title: string;
  traffic_light: IdeaTransferEvaluationResult["trafficLight"];
  summary: string;
}

interface APIIdeaTransferResult {
  traffic_light: IdeaTransferEvaluationResult["trafficLight"];
  headline: string;
  summary_markdown: string;
  estimated_tax_benefit_min_eur: number | null;
  estimated_tax_benefit_mid_eur: number | null;
  estimated_tax_benefit_max_eur: number | null;
  annual_tax_benefit_mid_eur: number | null;
  dimensions: APIIdeaTransferDimension[];
  required_documents: string[];
  next_actions: string[];
  sources: Source[];
  assumptions: string[];
}

interface APIIdeaTransferCase {
  session_id: string;
  case_kind: IdeaTransferCaseKind;
  status: IdeaTransferCase["status"];
  answers: {
    idea_summary?: string | null;
    origin_scope?: IdeaTransferAnswers["originScope"];
    connected_to_job_or_business?: IdeaTransferAnswers["connectedToJobOrBusiness"];
    is_paid_transfer?: IdeaTransferAnswers["isPaidTransfer"];
    purchase_price_eur?: number | null;
    consideration_type?: IdeaTransferAnswers["considerationType"];
    buyer_use_plan_available?: IdeaTransferAnswers["buyerUsePlanAvailable"];
    buyer_use_description?: string | null;
    valuation_mode?: IdeaTransferAnswers["valuationMode"];
    documentation_status?: IdeaTransferAnswers["documentationStatus"];
    family_value_alignment?: IdeaTransferAnswers["familyValueAlignment"];
    useful_life_years?: IdeaTransferAnswers["usefulLifeYears"];
  };
  result: APIIdeaTransferResult | null;
  updated_at: string;
}

interface APIInstagramImageRef {
  id: string;
  original_filename: string;
  stored_path: string;
  content_type: string;
  size_bytes: number;
}

interface APIInstagramFollowUpQuestion {
  id: string;
  prompt: string;
  answer?: string | null;
}

interface APIInstagramClaim {
  id: string;
  raw_text: string;
  edited_text: string;
  category: InstagramClaim["category"];
  return_bucket: InstagramClaim["returnBucket"];
  status: InstagramClaim["status"];
  selected_for_import: boolean;
  follow_up_questions: APIInstagramFollowUpQuestion[];
}

interface APIInstagramEvaluatedTip {
  claim_id: string;
  title: string;
  normalized_tip: string;
  category: InstagramEvaluatedTip["category"];
  return_bucket: InstagramEvaluatedTip["returnBucket"];
  traffic_light: InstagramEvaluatedTip["trafficLight"];
  explanation: string;
  estimated_saving_eur: number | null;
  required_evidence: string[];
  sources: Source[];
}

interface APIInstagramPostCheck {
  session_id: string;
  status: InstagramPostCheck["status"];
  images: APIInstagramImageRef[];
  claims: APIInstagramClaim[];
  evaluated_tips: APIInstagramEvaluatedTip[] | null;
  updated_at: string;
}

interface APITaxPrepItem {
  id: string;
  session_id: string;
  source: TaxPrepItem["source"];
  source_claim_id: string;
  title: string;
  category: TaxPrepItem["category"];
  return_bucket: TaxPrepItem["returnBucket"];
  estimated_saving_eur: number | null;
  risk_level: TaxPrepItem["riskLevel"];
  required_evidence: string[];
  summary: string;
  status: TaxPrepItem["status"];
  created_at: string;
  updated_at: string;
}

// ─── Mappers ──────────────────────────────────────────────────────────────────

function mapSession(s: APISession): Session {
  return {
    id: s.id,
    title: s.title,
    createdAt: new Date(s.created_at),
    messageCount: s.message_count,
    totalSaving: s.total_saving || undefined,
  };
}

function mapMessage(m: APIMessage): Message {
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    sources: m.sources ?? undefined,
    riskBadge: m.risk_badge ?? undefined,
    savingAmount: m.saving_amount ?? undefined,
    timestamp: new Date(m.created_at),
  };
}

function mapIdeaTransferResult(result: APIIdeaTransferResult): IdeaTransferEvaluationResult {
  return {
    trafficLight: result.traffic_light,
    headline: result.headline,
    summaryMarkdown: result.summary_markdown,
    estimatedTaxBenefitMinEur: result.estimated_tax_benefit_min_eur,
    estimatedTaxBenefitMidEur: result.estimated_tax_benefit_mid_eur,
    estimatedTaxBenefitMaxEur: result.estimated_tax_benefit_max_eur,
    annualTaxBenefitMidEur: result.annual_tax_benefit_mid_eur,
    dimensions: result.dimensions.map((dimension) => ({
      id: dimension.id,
      title: dimension.title,
      trafficLight: dimension.traffic_light,
      summary: dimension.summary,
    })),
    requiredDocuments: result.required_documents,
    nextActions: result.next_actions,
    sources: result.sources,
    assumptions: result.assumptions,
  };
}

function mapIdeaTransferCase(apiCase: APIIdeaTransferCase): IdeaTransferCase {
  return {
    sessionId: apiCase.session_id,
    caseKind: apiCase.case_kind,
    status: apiCase.status,
    answers: {
      ideaSummary: apiCase.answers.idea_summary,
      originScope: apiCase.answers.origin_scope,
      connectedToJobOrBusiness: apiCase.answers.connected_to_job_or_business,
      isPaidTransfer: apiCase.answers.is_paid_transfer,
      purchasePriceEur: apiCase.answers.purchase_price_eur,
      considerationType: apiCase.answers.consideration_type,
      buyerUsePlanAvailable: apiCase.answers.buyer_use_plan_available,
      buyerUseDescription: apiCase.answers.buyer_use_description,
      valuationMode: apiCase.answers.valuation_mode,
      documentationStatus: apiCase.answers.documentation_status,
      familyValueAlignment: apiCase.answers.family_value_alignment,
      usefulLifeYears: apiCase.answers.useful_life_years,
    },
    result: apiCase.result ? mapIdeaTransferResult(apiCase.result) : null,
    updatedAt: new Date(apiCase.updated_at),
  };
}

function mapInstagramCheck(apiCheck: APIInstagramPostCheck): InstagramPostCheck {
  return {
    sessionId: apiCheck.session_id,
    status: apiCheck.status,
    images: apiCheck.images.map((image) => ({
      id: image.id,
      originalFilename: image.original_filename,
      storedPath: image.stored_path,
      contentType: image.content_type,
      sizeBytes: image.size_bytes,
    })),
    claims: apiCheck.claims.map((claim) => ({
      id: claim.id,
      rawText: claim.raw_text,
      editedText: claim.edited_text,
      category: claim.category,
      returnBucket: claim.return_bucket,
      status: claim.status,
      selectedForImport: claim.selected_for_import,
      followUpQuestions: claim.follow_up_questions.map((question) => ({
        id: question.id,
        prompt: question.prompt,
        answer: question.answer ?? null,
      })),
    })),
    evaluatedTips: apiCheck.evaluated_tips
      ? apiCheck.evaluated_tips.map((tip) => ({
          claimId: tip.claim_id,
          title: tip.title,
          normalizedTip: tip.normalized_tip,
          category: tip.category,
          returnBucket: tip.return_bucket,
          trafficLight: tip.traffic_light,
          explanation: tip.explanation,
          estimatedSavingEur: tip.estimated_saving_eur,
          requiredEvidence: tip.required_evidence,
          sources: tip.sources,
        }))
      : null,
    updatedAt: new Date(apiCheck.updated_at),
  };
}

function mapTaxPrepItem(item: APITaxPrepItem): TaxPrepItem {
  return {
    id: item.id,
    sessionId: item.session_id,
    source: item.source,
    sourceClaimId: item.source_claim_id,
    title: item.title,
    category: item.category,
    returnBucket: item.return_bucket,
    estimatedSavingEur: item.estimated_saving_eur,
    riskLevel: item.risk_level,
    requiredEvidence: item.required_evidence,
    summary: item.summary,
    status: item.status,
    createdAt: new Date(item.created_at),
    updatedAt: new Date(item.updated_at),
  };
}

// ─── API calls ────────────────────────────────────────────────────────────────

export async function* streamChat(
  payload: ChatPayload,
  signal?: AbortSignal,
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  if (!response.body) {
    throw new Error("Response body is empty");
  }

  yield* parseSSEStream<StreamChunk>(response.body);
}

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/api/sessions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data: APISession[] = await res.json();
  return data.map(mapSession);
}

export async function fetchSessionMessages(
  sessionId: string,
  signal?: AbortSignal,
): Promise<Message[]> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data: APISessionDetail = await res.json();
  return data.messages.map(mapMessage);
}

export async function renameSession(sessionId: string, title: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 404) throw new Error(`HTTP ${res.status}`);
}

function toIdeaTransferPayload(
  caseKind: IdeaTransferCaseKind,
  answers: IdeaTransferAnswers,
) {
  return {
    case_kind: caseKind,
    answers: {
      idea_summary: answers.ideaSummary ?? null,
      origin_scope: answers.originScope ?? null,
      connected_to_job_or_business: answers.connectedToJobOrBusiness ?? null,
      is_paid_transfer: answers.isPaidTransfer ?? null,
      purchase_price_eur: answers.purchasePriceEur ?? null,
      consideration_type: answers.considerationType ?? null,
      buyer_use_plan_available: answers.buyerUsePlanAvailable ?? null,
      buyer_use_description: answers.buyerUseDescription ?? null,
      valuation_mode: answers.valuationMode ?? null,
      documentation_status: answers.documentationStatus ?? null,
      family_value_alignment: answers.familyValueAlignment ?? null,
      useful_life_years: answers.usefulLifeYears ?? null,
    },
  };
}

function toInstagramCheckPayload(payload: InstagramCheckSavePayload) {
  return {
    claims: payload.claims.map((claim) => ({
      id: claim.id,
      edited_text: claim.editedText,
      category: claim.category,
      return_bucket: claim.returnBucket,
      status: claim.status,
      selected_for_import: claim.selectedForImport,
      follow_up_questions: claim.followUpQuestions.map((question) => ({
        id: question.id,
        prompt: question.prompt,
        answer: question.answer ?? null,
      })),
    })),
  };
}

export async function fetchIdeaTransferCase(sessionId: string): Promise<IdeaTransferCase | null> {
  const res = await fetch(`${API_URL}/api/idea-transfer/${sessionId}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data: APIIdeaTransferCase = await res.json();
  return mapIdeaTransferCase(data);
}

export async function saveIdeaTransferDraft(
  sessionId: string,
  caseKind: IdeaTransferCaseKind,
  answers: IdeaTransferAnswers,
): Promise<IdeaTransferCase> {
  const res = await fetch(`${API_URL}/api/idea-transfer/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(toIdeaTransferPayload(caseKind, answers)),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data: APIIdeaTransferCase = await res.json();
  return mapIdeaTransferCase(data);
}

export async function evaluateIdeaTransferCase(
  sessionId: string,
  taxYear: number,
  caseKind: IdeaTransferCaseKind,
  answers: IdeaTransferAnswers,
): Promise<IdeaTransferCase> {
  const res = await fetch(`${API_URL}/api/idea-transfer/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      tax_year: taxYear,
      ...toIdeaTransferPayload(caseKind, answers),
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Ideen-Transfer-Check fehlgeschlagen (${res.status}): ${text}`);
  }
  const data: APIIdeaTransferCase = await res.json();
  return mapIdeaTransferCase(data);
}

export async function analyzeInstagramCheck(
  sessionId: string,
  taxYear: number,
  images: File[],
): Promise<InstagramPostCheck> {
  const formData = new FormData();
  formData.set("session_id", sessionId);
  formData.set("tax_year", String(taxYear));
  for (const image of images) {
    formData.append("images", image);
  }

  const res = await fetch(`${API_URL}/api/instagram-check/analyze`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Instagram-Check fehlgeschlagen (${res.status}): ${text}`);
  }
  const data: APIInstagramPostCheck = await res.json();
  return mapInstagramCheck(data);
}

export async function fetchInstagramCheck(
  sessionId: string,
): Promise<InstagramPostCheck | null> {
  const res = await fetch(`${API_URL}/api/instagram-check/${sessionId}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data: APIInstagramPostCheck = await res.json();
  return mapInstagramCheck(data);
}

export async function saveInstagramCheck(
  sessionId: string,
  payload: InstagramCheckSavePayload,
): Promise<InstagramPostCheck> {
  const res = await fetch(`${API_URL}/api/instagram-check/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(toInstagramCheckPayload(payload)),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Instagram-Check konnte nicht gespeichert werden (${res.status}): ${text}`);
  }
  const data: APIInstagramPostCheck = await res.json();
  return mapInstagramCheck(data);
}

export async function evaluateInstagramCheck(
  sessionId: string,
  taxYear: number,
): Promise<InstagramPostCheck> {
  const res = await fetch(`${API_URL}/api/instagram-check/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, tax_year: taxYear }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Instagram-Check Bewertung fehlgeschlagen (${res.status}): ${text}`);
  }
  const data: APIInstagramPostCheck = await res.json();
  return mapInstagramCheck(data);
}

export async function fetchTaxPrepItems(sessionId: string): Promise<TaxPrepItem[]> {
  const res = await fetch(`${API_URL}/api/tax-prep/${sessionId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data: APITaxPrepItem[] = await res.json();
  return data.map(mapTaxPrepItem);
}

export async function scanExpenses(
  expenses: Array<{ description: string; amount: number }>,
  context?: string,
  taxYear = 2025,
): Promise<ScanResult> {
  const res = await fetch(`${API_URL}/api/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      expenses,
      context: context?.trim() || null,
      tax_year: taxYear,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Scan fehlgeschlagen (${res.status}): ${text}`);
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data: any = await res.json();
  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    items: data.items.map((item: any) => ({
      description: item.description,
      amount: item.amount,
      deductible: item.deductible,
      deductibleAmount: item.deductible_amount,
      savingEstimate: item.saving_estimate,
      risk: item.risk,
      explanation: item.explanation,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      sources: (item.sources ?? []).map((s: any) => ({
        law: s.law,
        paragraph: s.paragraph,
        section: s.section ?? "",
      })),
    })),
    totalSavingEstimate: data.total_saving_estimate,
    missingPositions: data.missing_positions ?? [],
  };
}
