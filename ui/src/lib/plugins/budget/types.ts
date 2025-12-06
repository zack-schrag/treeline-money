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

/**
 * Transfer: move funds from one category to another (same or different) for next month
 * Stored in the source month's config
 */
export interface Transfer {
  id: string;           // unique id for editing/deleting
  fromCategory: string; // source category
  toCategory: string;   // destination category (can be same as source for simple rollover)
  amount: number;       // amount being transferred
}

export interface BudgetConfig {
  income: Record<string, BudgetConfigCategory>;
  expenses: Record<string, BudgetConfigCategory>;
  // Optional: ordering of categories (array of category names)
  incomeOrder?: string[];
  expensesOrder?: string[];
  // Optional: filter to only include certain accounts
  selectedAccounts?: string[];
  // Transfers to next month (flat list)
  transfers?: Transfer[];
}

export interface Transaction {
  transaction_id: string;
  transaction_date: string;
  description: string;
  amount: number;
  tags: string[];
  account_name: string;
}
