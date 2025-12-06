/**
 * Auto-Tag Rules Service
 *
 * Handles CRUD operations for tag rules and rule matching logic.
 */

import { getPluginSettings, updatePluginSettings, executeQuery } from "../../../sdk";
import type {
  TagRule,
  RuleCondition,
  TransactionsPluginSettings,
  RuleTestResult,
} from "./types";
import { DEFAULT_TRANSACTIONS_SETTINGS } from "./types";

const PLUGIN_ID = "transactions";

/**
 * Generate a unique ID for a rule
 */
export function generateRuleId(): string {
  return `rule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Load all rules from settings
 */
export async function loadRules(): Promise<TagRule[]> {
  const settings = await getPluginSettings<TransactionsPluginSettings>(
    PLUGIN_ID,
    DEFAULT_TRANSACTIONS_SETTINGS
  );
  return settings.rules || [];
}

/**
 * Save a new rule
 */
export async function saveRule(rule: TagRule): Promise<void> {
  const settings = await getPluginSettings<TransactionsPluginSettings>(
    PLUGIN_ID,
    DEFAULT_TRANSACTIONS_SETTINGS
  );
  settings.rules = [...(settings.rules || []), rule];
  await updatePluginSettings(PLUGIN_ID, settings);
}

/**
 * Update an existing rule
 */
export async function updateRule(rule: TagRule): Promise<void> {
  const settings = await getPluginSettings<TransactionsPluginSettings>(
    PLUGIN_ID,
    DEFAULT_TRANSACTIONS_SETTINGS
  );
  const index = settings.rules.findIndex((r) => r.id === rule.id);
  if (index >= 0) {
    settings.rules[index] = { ...rule, updatedAt: new Date().toISOString() };
    await updatePluginSettings(PLUGIN_ID, settings);
  }
}

/**
 * Delete a rule by ID
 */
export async function deleteRule(ruleId: string): Promise<void> {
  const settings = await getPluginSettings<TransactionsPluginSettings>(
    PLUGIN_ID,
    DEFAULT_TRANSACTIONS_SETTINGS
  );
  settings.rules = settings.rules.filter((r) => r.id !== ruleId);
  await updatePluginSettings(PLUGIN_ID, settings);
}

/**
 * Toggle rule enabled state
 */
export async function toggleRuleEnabled(ruleId: string): Promise<void> {
  const settings = await getPluginSettings<TransactionsPluginSettings>(
    PLUGIN_ID,
    DEFAULT_TRANSACTIONS_SETTINGS
  );
  const rule = settings.rules.find((r) => r.id === ruleId);
  if (rule) {
    rule.enabled = !rule.enabled;
    rule.updatedAt = new Date().toISOString();
    await updatePluginSettings(PLUGIN_ID, settings);
  }
}

/**
 * Check if a single condition matches a transaction
 */
function matchCondition(
  condition: RuleCondition,
  description: string,
  amount: number,
  accountName: string
): boolean {
  const { field, operator, value, value2 } = condition;

  // Get the field value to test
  let fieldValue: string | number;
  switch (field) {
    case "description":
      fieldValue = description.toLowerCase();
      break;
    case "amount":
      fieldValue = amount;
      break;
    case "account":
      fieldValue = accountName.toLowerCase();
      break;
    default:
      return false;
  }

  // Apply operator
  switch (operator) {
    case "contains":
      return typeof fieldValue === "string" && fieldValue.includes(String(value).toLowerCase());
    case "starts_with":
      return typeof fieldValue === "string" && fieldValue.startsWith(String(value).toLowerCase());
    case "ends_with":
      return typeof fieldValue === "string" && fieldValue.endsWith(String(value).toLowerCase());
    case "equals":
      if (typeof fieldValue === "string") {
        return fieldValue === String(value).toLowerCase();
      }
      return fieldValue === Number(value);
    case "regex":
      try {
        const regex = new RegExp(String(value), "i");
        return typeof fieldValue === "string" && regex.test(fieldValue);
      } catch {
        return false;
      }
    case "greater_than":
      return typeof fieldValue === "number" && fieldValue > Number(value);
    case "less_than":
      return typeof fieldValue === "number" && fieldValue < Number(value);
    case "between":
      return (
        typeof fieldValue === "number" &&
        fieldValue >= Number(value) &&
        fieldValue <= Number(value2 ?? value)
      );
    default:
      return false;
  }
}

/**
 * Check if a rule matches a transaction
 */
export function matchesRule(
  rule: TagRule,
  description: string,
  amount: number,
  accountName: string
): boolean {
  if (!rule.enabled || rule.conditions.length === 0) {
    return false;
  }

  const results = rule.conditions.map((cond) =>
    matchCondition(cond, description, amount, accountName)
  );

  if (rule.conditionLogic === "all") {
    return results.every((r) => r);
  } else {
    return results.some((r) => r);
  }
}

/**
 * Get the WHERE clause for a rule
 * Prefers sqlCondition if available, otherwise builds from conditions
 */
export function getRuleWhereClause(rule: TagRule): string | null {
  // Prefer SQL condition if available
  if (rule.sqlCondition && rule.sqlCondition.trim()) {
    return rule.sqlCondition.trim();
  }

  // Fall back to building from conditions
  const sqlConditions = buildSqlConditions(rule);
  if (!sqlConditions) {
    return null;
  }

  const logic = rule.conditionLogic === "all" ? " AND " : " OR ";
  return sqlConditions.join(logic);
}

/**
 * Test a rule against existing transactions in the database
 */
export async function testRule(rule: TagRule, limit: number = 10): Promise<RuleTestResult> {
  const whereClause = getRuleWhereClause(rule);

  if (!whereClause) {
    return { matchingCount: 0, sampleMatches: [] };
  }

  try {
    // Count total matches
    const countResult = await executeQuery(`
      SELECT COUNT(*) as cnt
      FROM transactions
      WHERE ${whereClause}
    `);
    const matchingCount = (countResult.rows[0]?.[0] as number) || 0;

    // Get sample matches
    const sampleResult = await executeQuery(`
      SELECT transaction_id, description, amount, account_name
      FROM transactions
      WHERE ${whereClause}
      ORDER BY transaction_date DESC
      LIMIT ${limit}
    `);

    const sampleMatches = sampleResult.rows.map((row) => ({
      transaction_id: row[0] as string,
      description: row[1] as string,
      amount: row[2] as number,
      account_name: row[3] as string,
    }));

    return { matchingCount, sampleMatches };
  } catch (e) {
    console.error("Failed to test rule:", e);
    return { matchingCount: 0, sampleMatches: [] };
  }
}

/**
 * Test a raw SQL WHERE clause against existing transactions
 */
export async function testSqlCondition(sqlCondition: string, limit: number = 10): Promise<RuleTestResult> {
  if (!sqlCondition.trim()) {
    return { matchingCount: 0, sampleMatches: [] };
  }

  try {
    // Count total matches
    const countResult = await executeQuery(`
      SELECT COUNT(*) as cnt
      FROM transactions
      WHERE ${sqlCondition}
    `);
    const matchingCount = (countResult.rows[0]?.[0] as number) || 0;

    // Get sample matches
    const sampleResult = await executeQuery(`
      SELECT transaction_id, description, amount, account_name
      FROM transactions
      WHERE ${sqlCondition}
      ORDER BY transaction_date DESC
      LIMIT ${limit}
    `);

    const sampleMatches = sampleResult.rows.map((row) => ({
      transaction_id: row[0] as string,
      description: row[1] as string,
      amount: row[2] as number,
      account_name: row[3] as string,
    }));

    return { matchingCount, sampleMatches };
  } catch (e) {
    console.error("Failed to test SQL condition:", e);
    throw e; // Re-throw so UI can show the error
  }
}

/**
 * Build SQL conditions from rule conditions
 */
function buildSqlConditions(rule: TagRule): string[] | null {
  if (rule.conditions.length === 0) {
    return null;
  }

  const conditions: string[] = [];

  for (const cond of rule.conditions) {
    const sql = conditionToSql(cond);
    if (sql) {
      conditions.push(sql);
    }
  }

  return conditions.length > 0 ? conditions : null;
}

/**
 * Convert a single condition to SQL
 */
function conditionToSql(condition: RuleCondition): string | null {
  const { field, operator, value, value2 } = condition;

  // Map field to column name
  let column: string;
  switch (field) {
    case "description":
      column = "description";
      break;
    case "amount":
      column = "amount";
      break;
    case "account":
      column = "account_name";
      break;
    default:
      return null;
  }

  // Escape single quotes in string values
  const escapedValue = String(value).replace(/'/g, "''");

  switch (operator) {
    case "contains":
      return `LOWER(${column}) LIKE '%${escapedValue.toLowerCase()}%'`;
    case "starts_with":
      return `LOWER(${column}) LIKE '${escapedValue.toLowerCase()}%'`;
    case "ends_with":
      return `LOWER(${column}) LIKE '%${escapedValue.toLowerCase()}'`;
    case "equals":
      if (field === "amount") {
        return `${column} = ${Number(value)}`;
      }
      return `LOWER(${column}) = '${escapedValue.toLowerCase()}'`;
    case "regex":
      // DuckDB uses regexp_matches
      return `regexp_matches(LOWER(${column}), '${escapedValue.toLowerCase()}')`;
    case "greater_than":
      return `${column} > ${Number(value)}`;
    case "less_than":
      return `${column} < ${Number(value)}`;
    case "between":
      return `${column} BETWEEN ${Number(value)} AND ${Number(value2 ?? value)}`;
    default:
      return null;
  }
}

/**
 * Create a rule from a transaction description (extract pattern)
 */
export function createRuleFromTransaction(
  description: string,
  tags: string[],
  accountName?: string
): Partial<TagRule> {
  // Extract merchant pattern (similar to frequency suggester)
  const pattern = extractMerchantPattern(description);

  const conditions: RuleCondition[] = [];

  if (pattern) {
    conditions.push({
      field: "description",
      operator: "contains",
      value: pattern,
    });
  }

  return {
    id: generateRuleId(),
    name: pattern ? `Tag "${pattern}" as ${tags.join(", ")}` : `Tag as ${tags.join(", ")}`,
    conditions,
    conditionLogic: "all",
    tags,
    enabled: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

/**
 * Extract a merchant pattern from a transaction description.
 * Similar logic to FrequencyBasedSuggester.
 */
function extractMerchantPattern(description: string): string | null {
  if (!description) return null;

  // Clean up the description
  const cleaned = description
    .toUpperCase()
    .replace(/[*#]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  // Take first word as merchant pattern
  const words = cleaned.split(" ").filter((w) => w.length > 2);
  if (words.length === 0) return null;

  // Use first word, or first two if first is very short
  if (words[0].length <= 3 && words.length > 1) {
    return words.slice(0, 2).join(" ");
  }

  return words[0];
}

/**
 * Generate a SQL WHERE clause suggestion from transaction descriptions.
 * Analyzes the descriptions to find common patterns and suggests an appropriate clause.
 */
export function generateSqlFromTransactions(descriptions: string[]): {
  sql: string;
  pattern: string | null;
  confidence: "high" | "medium" | "low";
} {
  if (descriptions.length === 0) {
    return { sql: "", pattern: null, confidence: "low" };
  }

  // Extract patterns from all descriptions
  const patterns = descriptions.map(extractMerchantPattern).filter((p): p is string => p !== null);

  if (patterns.length === 0) {
    // No patterns found, use first description as-is
    const escaped = descriptions[0].replace(/'/g, "''");
    return {
      sql: `LOWER(description) LIKE '%${escaped.toLowerCase()}%'`,
      pattern: descriptions[0],
      confidence: "low",
    };
  }

  // Find the most common pattern
  const patternCounts = new Map<string, number>();
  for (const p of patterns) {
    patternCounts.set(p, (patternCounts.get(p) || 0) + 1);
  }

  // Sort by count descending
  const sortedPatterns = [...patternCounts.entries()].sort((a, b) => b[1] - a[1]);
  const topPattern = sortedPatterns[0][0];
  const topCount = sortedPatterns[0][1];

  // Determine confidence based on how many descriptions share the pattern
  const confidence: "high" | "medium" | "low" =
    topCount === descriptions.length ? "high" : topCount > descriptions.length / 2 ? "medium" : "low";

  // Escape single quotes for SQL
  const escaped = topPattern.replace(/'/g, "''");

  return {
    sql: `LOWER(description) LIKE '%${escaped.toLowerCase()}%'`,
    pattern: topPattern,
    confidence,
  };
}

/**
 * Get human-readable description of a condition
 */
export function describeCondition(condition: RuleCondition): string {
  const { field, operator, value, value2 } = condition;

  const fieldLabel = field === "description" ? "Description" : field === "amount" ? "Amount" : "Account";

  switch (operator) {
    case "contains":
      return `${fieldLabel} contains "${value}"`;
    case "starts_with":
      return `${fieldLabel} starts with "${value}"`;
    case "ends_with":
      return `${fieldLabel} ends with "${value}"`;
    case "equals":
      return `${fieldLabel} equals "${value}"`;
    case "regex":
      return `${fieldLabel} matches /${value}/`;
    case "greater_than":
      return `${fieldLabel} > ${value}`;
    case "less_than":
      return `${fieldLabel} < ${value}`;
    case "between":
      return `${fieldLabel} between ${value} and ${value2}`;
    default:
      return `${fieldLabel} ${operator} ${value}`;
  }
}

/**
 * Get human-readable description of a rule
 */
export function describeRule(rule: TagRule): string {
  if (rule.conditions.length === 0) {
    return "No conditions";
  }

  const conditionDescs = rule.conditions.map(describeCondition);
  const logic = rule.conditionLogic === "all" ? " AND " : " OR ";
  return conditionDescs.join(logic);
}
