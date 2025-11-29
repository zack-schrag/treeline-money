/**
 * Accounts Plugin Types
 */

export type BalanceClassification = "asset" | "liability";

export interface Account {
  account_id: string;
  name: string;
  nickname: string | null;
  account_type: string | null;
  currency: string;
  balance: number | null;
  institution_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountWithStats extends Account {
  transaction_count: number;
  first_transaction: string | null;
  last_transaction: string | null;
  computed_balance: number;
  balance_as_of: string | null;
  classification: BalanceClassification;
}

export interface BalanceSnapshot {
  snapshot_id: string;
  account_id: string;
  balance: number;
  snapshot_time: string;
}

export interface BalanceTrendPoint {
  month: string;
  day: number;
  balance: number;
  snapshot_time: string;
}

export interface AccountsConfig {
  // Override balance classification for accounts (account_id -> classification)
  classificationOverrides: Record<string, BalanceClassification>;
  // Accounts excluded from net worth calculation
  excludedFromNetWorth: string[];
}

// Default asset/liability mapping based on account_type
export function getDefaultClassification(accountType: string | null): BalanceClassification {
  if (!accountType) return "asset";
  const liabilityTypes = ["credit", "loan"];
  return liabilityTypes.includes(accountType.toLowerCase()) ? "liability" : "asset";
}
