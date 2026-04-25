import type { Source } from "./chat";

export type IdeaTransferTrafficLight = "green" | "yellow" | "red";
export type IdeaTransferCaseKind = "own_gmbh_sale" | "family_transfer";
export type IdeaTransferCaseStatus = "draft" | "completed";
export type IdeaTransferOriginScope = "private" | "professional" | "unclear";
export type IdeaTransferYesNoUnclear = "yes" | "no" | "unclear";
export type IdeaTransferConsiderationType = "cash" | "asset_transfer" | "mixed" | "unclear";
export type IdeaTransferValuationMode = "external" | "internal" | "none" | "unclear";
export type IdeaTransferDocumentationStatus = "complete" | "partial" | "none" | "unclear";
export type IdeaTransferUsefulLifeYears = 3 | 5 | 10 | "unclear";
export type IdeaTransferDimensionId =
  | "private_origin"
  | "employment_proximity"
  | "transferability"
  | "valuation"
  | "acquirer_use_plan"
  | "transfer_tax";

export interface IdeaTransferAnswers {
  ideaSummary?: string | null;
  originScope?: IdeaTransferOriginScope | null;
  connectedToJobOrBusiness?: IdeaTransferYesNoUnclear | null;
  isPaidTransfer?: IdeaTransferYesNoUnclear | null;
  purchasePriceEur?: number | null;
  considerationType?: IdeaTransferConsiderationType | null;
  buyerUsePlanAvailable?: IdeaTransferYesNoUnclear | null;
  buyerUseDescription?: string | null;
  valuationMode?: IdeaTransferValuationMode | null;
  documentationStatus?: IdeaTransferDocumentationStatus | null;
  familyValueAlignment?: IdeaTransferYesNoUnclear | null;
  usefulLifeYears?: IdeaTransferUsefulLifeYears | null;
}

export interface IdeaTransferDimension {
  id: IdeaTransferDimensionId;
  title: string;
  trafficLight: IdeaTransferTrafficLight;
  summary: string;
}

export interface IdeaTransferEvaluationResult {
  trafficLight: IdeaTransferTrafficLight;
  headline: string;
  summaryMarkdown: string;
  estimatedTaxBenefitMinEur?: number | null;
  estimatedTaxBenefitMidEur?: number | null;
  estimatedTaxBenefitMaxEur?: number | null;
  annualTaxBenefitMidEur?: number | null;
  dimensions: IdeaTransferDimension[];
  requiredDocuments: string[];
  nextActions: string[];
  sources: Source[];
  assumptions: string[];
}

export interface IdeaTransferCase {
  sessionId: string;
  caseKind: IdeaTransferCaseKind;
  status: IdeaTransferCaseStatus;
  answers: IdeaTransferAnswers;
  result?: IdeaTransferEvaluationResult | null;
  updatedAt: Date;
}

export interface IdeaTransferDraftPayload {
  caseKind: IdeaTransferCaseKind;
  answers: IdeaTransferAnswers;
}

