import type { Source } from "./chat";

export type InstagramCheckStatus = "draft" | "evaluated";
export type InstagramClaimStatus = "active" | "removed";
export type InstagramTrafficLight = "green" | "yellow" | "red";
export type TaxPrepRiskLevel = "low" | "medium" | "high";
export type InstagramTipCategory =
  | "arbeitsmittel"
  | "homeoffice"
  | "pendeln"
  | "weiterbildung"
  | "sonderausgaben"
  | "vorsorge"
  | "haushaltsnahe_dienstleistungen"
  | "kinder/familie"
  | "kapital"
  | "betriebsausgaben"
  | "other";
export type InstagramReturnBucket =
  | "anlage_n"
  | "betriebsausgaben"
  | "sonderausgaben"
  | "vorsorge"
  | "haushaltsnahe_dienstleistungen"
  | "kinder/familie"
  | "kapital"
  | "other";

export interface InstagramImageRef {
  id: string;
  originalFilename: string;
  storedPath: string;
  contentType: string;
  sizeBytes: number;
}

export interface InstagramFollowUpQuestion {
  id: string;
  prompt: string;
  answer?: string | null;
}

export interface InstagramClaim {
  id: string;
  rawText: string;
  editedText: string;
  category: InstagramTipCategory;
  returnBucket: InstagramReturnBucket;
  status: InstagramClaimStatus;
  selectedForImport: boolean;
  followUpQuestions: InstagramFollowUpQuestion[];
}

export interface InstagramEvaluatedTip {
  claimId: string;
  title: string;
  normalizedTip: string;
  category: InstagramTipCategory;
  returnBucket: InstagramReturnBucket;
  trafficLight: InstagramTrafficLight;
  explanation: string;
  estimatedSavingEur?: number | null;
  requiredEvidence: string[];
  sources: Source[];
}

export interface InstagramPostCheck {
  sessionId: string;
  status: InstagramCheckStatus;
  images: InstagramImageRef[];
  claims: InstagramClaim[];
  evaluatedTips?: InstagramEvaluatedTip[] | null;
  updatedAt: Date;
}

export interface InstagramCheckSavePayload {
  claims: InstagramClaim[];
}

export interface TaxPrepItem {
  id: string;
  sessionId: string;
  source: "instagram_post";
  sourceClaimId: string;
  title: string;
  category: InstagramTipCategory;
  returnBucket: InstagramReturnBucket;
  estimatedSavingEur?: number | null;
  riskLevel: TaxPrepRiskLevel;
  requiredEvidence: string[];
  summary: string;
  status: "confirmed";
  createdAt: Date;
  updatedAt: Date;
}
