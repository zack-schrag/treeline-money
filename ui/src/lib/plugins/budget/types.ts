/**
 * Budget Plugin Types
 */

export type BudgetType = "income" | "expense";
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
  net: number;
}

export interface BudgetConfigCategory {
  expected: number;
  tags: string[];
  require_all?: boolean;
  amount_sign?: AmountSign;
}

/** Rollover entry: amount carried from a previous month */
export interface RolloverEntry {
  amount: number;  // positive = surplus, negative = deficit
  from: string;    // source month (YYYY-MM)
}

export interface BudgetConfig {
  income: Record<string, BudgetConfigCategory>;
  expenses: Record<string, BudgetConfigCategory>;
  // Optional: ordering of categories (array of category names)
  incomeOrder?: string[];
  expensesOrder?: string[];
  // Optional: filter to only include certain accounts
  selectedAccounts?: string[];
  // Optional: rollovers from previous months (keyed by category name)
  rollovers?: Record<string, RolloverEntry>;
}

export interface Transaction {
  transaction_id: string;
  transaction_date: string;
  description: string;
  amount: number;
  tags: string[];
  account_name: string;
}
