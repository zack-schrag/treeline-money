/**
 * Budget Plugin Types
 */

export type BudgetType = "income" | "expense" | "savings";
export type AmountSign = "positive" | "negative" | "any";

export interface BudgetCategory {
  id: string;
  type: BudgetType;
  category: string;
  expected: number;
  tags: string[];
  require_all: boolean;
  amount_sign: AmountSign | null;
}

export interface BudgetActual {
  id: string;
  type: BudgetType;
  category: string;
  expected: number;
  actual: number;
  variance: number;
  percentUsed: number;
}

export interface MonthSummary {
  month: string;
  income: number;
  expenses: number;
  savings: number;
  net: number;
}

export interface BudgetConfig {
  income: Record<string, { expected: number; tags: string[]; require_all?: boolean; amount_sign?: AmountSign }>;
  expenses: Record<string, { expected: number; tags: string[]; require_all?: boolean; amount_sign?: AmountSign }>;
  savings: Record<string, { expected: number; tags: string[]; require_all?: boolean; amount_sign?: AmountSign }>;
  // Optional: filter to only include certain accounts
  selectedAccounts?: string[];
}

export interface Transaction {
  transaction_id: string;
  transaction_date: string;
  description: string;
  amount: number;
  tags: string[];
  account_name: string;
}
