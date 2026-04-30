import type { Source } from "./chat";

export type TaxInterviewStatus = "in_progress" | "completed" | "evaluated";
export type TaxInterviewAnswerType = "bool" | "choice" | "number" | "text";
export type TaxInterviewTrafficLight = "green" | "yellow" | "red";

export interface InterviewQuestion {
  id: string;
  category: string;
  text: string;
  answerType: TaxInterviewAnswerType;
  options: string[] | null;
}

export interface TaxInterviewFinding {
  category: string;
  title: string;
  trafficLight: TaxInterviewTrafficLight;
  explanation: string;
  estimatedSavingEur: number | null;
  requiredEvidence: string[];
  sources: Source[];
}

export interface TaxInterview {
  sessionId: string;
  status: TaxInterviewStatus;
  taxYear: number;
  answers: Record<string, boolean | number | string>;
  nextQuestion: InterviewQuestion | null;
  findings: TaxInterviewFinding[] | null;
  updatedAt: Date;
}
