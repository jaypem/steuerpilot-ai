export interface ScanExpenseItem {
  /** Client-side only — used as React key */
  id: string;
  description: string;
  /** String while editing, parsed to number on submit */
  amount: string;
}

export interface ScanSourceRef {
  law: string;
  paragraph: string;
  section: string;
}

export interface ScannedExpense {
  description: string;
  amount: number;
  deductible: boolean;
  deductibleAmount: number;
  savingEstimate: number;
  risk: "low" | "medium" | "high";
  explanation: string;
  sources: ScanSourceRef[];
}

export interface ScanResult {
  items: ScannedExpense[];
  totalSavingEstimate: number;
  missingPositions: string[];
}
