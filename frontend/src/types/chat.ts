export interface Source {
  law: string;       // z.B. "EStG"
  paragraph: string; // z.B. "§ 9"
  section: string;   // z.B. "Abs. 1"
  text: string;      // Volltext des Chunks (für aufgeklappte Ansicht)
  url?: string;
}

export type RiskLevel = "low" | "medium" | "high";

export interface RiskBadge {
  level: RiskLevel;
  label: string;       // z.B. "Unstreitig", "Grauzone", "Strittig"
  explanation: string; // Tooltip-Text
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  riskBadge?: RiskBadge;
  savingAmount?: number; // geschätzte Steuerersparnis in €
  timestamp: Date;
  isStreaming?: boolean;
  statusLabel?: string;
}
