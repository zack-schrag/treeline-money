/**
 * Auto-Tag Rules Types
 *
 * Rules are stored in settings.json under plugins.transactions.rules
 */

/**
 * Condition types for rule matching
 */
export type ConditionOperator =
  | "contains"      // description contains string (case-insensitive)
  | "starts_with"   // description starts with string
  | "ends_with"     // description ends with string
  | "equals"        // exact match
  | "regex"         // regex pattern match
  | "greater_than"  // amount > value
  | "less_than"     // amount < value
  | "between";      // amount between min and max

export interface RuleCondition {
  field: "description" | "amount" | "account";
  operator: ConditionOperator;
  value: string | number;
  value2?: number; // For "between" operator
}

/**
 * A single auto-tag rule
 *
 * Rules can be defined in two ways:
 * 1. SQL-based (preferred): A raw SQL WHERE clause stored in `sqlCondition`
 * 2. Condition-based (legacy): Array of `conditions` with `conditionLogic`
 *
 * If both are present, sqlCondition takes precedence.
 */
export interface TagRule {
  id: string;
  name: string;
  // SQL-based rule (preferred) - a raw WHERE clause
  sqlCondition?: string;
  // Condition-based rule (legacy fallback)
  conditions: RuleCondition[];
  conditionLogic: "all" | "any"; // AND vs OR
  tags: string[];
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
  // Stats (optional, for display)
  matchCount?: number;
}

/**
 * Plugin settings shape for transactions plugin
 */
export interface TransactionsPluginSettings {
  rules: TagRule[];
  [key: string]: unknown; // Allow indexing for Record<string, unknown> constraint
}

/**
 * Default settings
 */
export const DEFAULT_TRANSACTIONS_SETTINGS: TransactionsPluginSettings = {
  rules: [],
};

/**
 * Result of testing a rule against transactions
 */
export interface RuleTestResult {
  matchingCount: number;
  sampleMatches: Array<{
    transaction_id: string;
    description: string;
    amount: number;
    account_name: string;
  }>;
}
