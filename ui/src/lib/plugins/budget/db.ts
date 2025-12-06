/**
 * Budget Database Service
 *
 * Handles all budget data persistence via DuckDB.
 *
 * DESIGN: Month-scoped categories
 * - Each month has its own complete set of categories (no template/override concept)
 * - Category IDs are UUIDs (not derived from name)
 * - Same category name can exist in different months with different configs
 * - Simpler ad-hoc queries (just filter by month)
 */

import { executeQuery } from "../../sdk";
import type { BudgetCategory, BudgetConfig, BudgetConfigCategory, Transfer, AmountSign } from "./types";

// ============================================================================
// CATEGORY OPERATIONS (Month-Scoped)
// ============================================================================

/**
 * Load all budget categories for a specific month
 */
export async function loadCategories(month: string): Promise<BudgetCategory[]> {
  const result = await executeQuery(`
    SELECT
      category_id,
      type,
      name,
      expected,
      tags,
      require_all,
      amount_sign,
      sort_order
    FROM sys_plugin_budget_categories
    WHERE month = '${month}'
    ORDER BY type DESC, sort_order ASC
  `);

  return result.rows.map((row) => ({
    id: row[0] as string,
    type: row[1] as "income" | "expense",
    category: row[2] as string,
    expected: row[3] as number,
    tags: (row[4] as string[]) || [],
    require_all: row[5] as boolean,
    amount_sign: row[6] as AmountSign | null,
  }));
}

/**
 * Check if a month has any categories
 */
export async function hasCategories(month: string): Promise<boolean> {
  const result = await executeQuery(`
    SELECT COUNT(*) FROM sys_plugin_budget_categories WHERE month = '${month}'
  `);
  return (result.rows[0]?.[0] as number) > 0;
}

/**
 * Save a single category (insert or update)
 */
export async function saveCategory(month: string, category: BudgetCategory, sortOrder: number): Promise<void> {
  const tagsArray = category.tags.map((t) => `'${t.replace(/'/g, "''")}'`).join(", ");
  const amountSignValue = category.amount_sign ? `'${category.amount_sign}'` : "NULL";

  await executeQuery(
    `
    INSERT INTO sys_plugin_budget_categories
      (category_id, month, type, name, expected, tags, require_all, amount_sign, sort_order, updated_at)
    VALUES
      ('${category.id}', '${month}', '${category.type}', '${category.category.replace(/'/g, "''")}',
       ${category.expected}, [${tagsArray}], ${category.require_all}, ${amountSignValue}, ${sortOrder}, now())
    ON CONFLICT (category_id) DO UPDATE SET
      month = EXCLUDED.month,
      type = EXCLUDED.type,
      name = EXCLUDED.name,
      expected = EXCLUDED.expected,
      tags = EXCLUDED.tags,
      require_all = EXCLUDED.require_all,
      amount_sign = EXCLUDED.amount_sign,
      sort_order = EXCLUDED.sort_order,
      updated_at = now()
    `,
    { readonly: false }
  );
}

/**
 * Save all categories for a month (replaces all existing for that month)
 */
export async function saveAllCategories(month: string, categories: BudgetCategory[]): Promise<void> {
  // Delete all existing categories for this month
  await executeQuery(`DELETE FROM sys_plugin_budget_categories WHERE month = '${month}'`, { readonly: false });

  // Insert all categories with sort order
  for (let i = 0; i < categories.length; i++) {
    await saveCategory(month, categories[i], i);
  }
}

/**
 * Delete a category
 */
export async function deleteCategory(categoryId: string): Promise<void> {
  await executeQuery(
    `DELETE FROM sys_plugin_budget_categories WHERE category_id = '${categoryId}'`,
    { readonly: false }
  );
}

/**
 * Copy categories from one month to another
 * Creates new UUIDs for the target month
 */
export async function copyFromMonth(sourceMonth: string, targetMonth: string): Promise<BudgetCategory[]> {
  // Load source categories
  const sourceCategories = await loadCategories(sourceMonth);

  if (sourceCategories.length === 0) {
    return [];
  }

  // Generate new UUIDs for target month
  const targetCategories = sourceCategories.map((cat) => ({
    ...cat,
    id: crypto.randomUUID(),
  }));

  // Save to target month
  await saveAllCategories(targetMonth, targetCategories);

  return targetCategories;
}

/**
 * Get list of months that have budget data
 */
export async function getMonthsWithData(): Promise<string[]> {
  const result = await executeQuery(`
    SELECT DISTINCT month FROM sys_plugin_budget_categories ORDER BY month DESC
  `);
  return result.rows.map((row) => row[0] as string);
}

// ============================================================================
// ROLLOVER OPERATIONS
// ============================================================================

/**
 * Load rollovers FROM a specific month (outgoing)
 */
export async function loadOutgoingRollovers(sourceMonth: string): Promise<Transfer[]> {
  const result = await executeQuery(`
    SELECT rollover_id, from_category, to_category, to_month, amount
    FROM sys_plugin_budget_rollovers
    WHERE source_month = '${sourceMonth}'
  `);

  return result.rows.map((row) => ({
    id: row[0] as string,
    fromCategory: row[1] as string,
    toCategory: row[2] as string,
    amount: row[4] as number,
  }));
}

/**
 * Load rollovers TO a specific month (incoming)
 */
export async function loadIncomingRollovers(targetMonth: string): Promise<Transfer[]> {
  const result = await executeQuery(`
    SELECT rollover_id, from_category, to_category, source_month, amount
    FROM sys_plugin_budget_rollovers
    WHERE to_month = '${targetMonth}'
  `);

  return result.rows.map((row) => ({
    id: row[0] as string,
    fromCategory: row[1] as string,
    toCategory: row[2] as string,
    amount: row[4] as number,
  }));
}

/**
 * Save a rollover
 */
export async function saveRollover(
  sourceMonth: string,
  toMonth: string,
  rollover: Transfer
): Promise<void> {
  await executeQuery(
    `
    INSERT INTO sys_plugin_budget_rollovers
      (rollover_id, source_month, from_category, to_category, to_month, amount)
    VALUES
      ('${rollover.id}', '${sourceMonth}', '${rollover.fromCategory.replace(/'/g, "''")}',
       '${rollover.toCategory.replace(/'/g, "''")}', '${toMonth}', ${rollover.amount})
    ON CONFLICT (rollover_id) DO UPDATE SET
      from_category = EXCLUDED.from_category,
      to_category = EXCLUDED.to_category,
      to_month = EXCLUDED.to_month,
      amount = EXCLUDED.amount
    `,
    { readonly: false }
  );
}

/**
 * Delete a rollover
 */
export async function deleteRollover(rolloverId: string): Promise<void> {
  await executeQuery(
    `DELETE FROM sys_plugin_budget_rollovers WHERE rollover_id = '${rolloverId}'`,
    { readonly: false }
  );
}

/**
 * Delete all rollovers from a specific month
 */
export async function deleteMonthRollovers(sourceMonth: string): Promise<void> {
  await executeQuery(
    `DELETE FROM sys_plugin_budget_rollovers WHERE source_month = '${sourceMonth}'`,
    { readonly: false }
  );
}

/**
 * Save multiple rollovers for a month (replaces existing)
 */
export async function saveMonthRollovers(
  sourceMonth: string,
  toMonth: string,
  rollovers: Transfer[]
): Promise<void> {
  // Delete existing rollovers from this source month
  await deleteMonthRollovers(sourceMonth);

  // Insert new rollovers
  for (const rollover of rollovers) {
    await saveRollover(sourceMonth, toMonth, rollover);
  }
}

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

/**
 * Load the complete budget data for a month
 */
export async function loadMonthData(month: string): Promise<{
  categories: BudgetCategory[];
  outgoingRollovers: Transfer[];
  incomingRollovers: Transfer[];
}> {
  const categories = await loadCategories(month);
  const outgoingRollovers = await loadOutgoingRollovers(month);
  const incomingRollovers = await loadIncomingRollovers(month);

  return {
    categories,
    outgoingRollovers,
    incomingRollovers,
  };
}

/**
 * Convert categories array to BudgetConfig format (for compatibility)
 */
export function categoriesToConfig(categories: BudgetCategory[]): BudgetConfig {
  const config: BudgetConfig = { income: {}, expenses: {} };
  const incomeOrder: string[] = [];
  const expensesOrder: string[] = [];

  for (const cat of categories) {
    const data: BudgetConfigCategory = {
      expected: cat.expected,
      tags: cat.tags,
    };
    if (cat.require_all) data.require_all = true;
    if (cat.amount_sign) data.amount_sign = cat.amount_sign;

    if (cat.type === "income") {
      config.income[cat.category] = data;
      incomeOrder.push(cat.category);
    } else {
      config.expenses[cat.category] = data;
      expensesOrder.push(cat.category);
    }
  }

  config.incomeOrder = incomeOrder;
  config.expensesOrder = expensesOrder;
  return config;
}

/**
 * Convert BudgetConfig to categories array (for migration)
 * Generates UUIDs for each category
 */
export function configToCategories(config: BudgetConfig): BudgetCategory[] {
  const result: BudgetCategory[] = [];

  // Get income categories in order
  const incomeNames = config.incomeOrder || Object.keys(config.income || {});
  for (const category of incomeNames) {
    const data = config.income?.[category];
    if (data) {
      result.push({
        id: crypto.randomUUID(),
        type: "income",
        category,
        expected: data.expected,
        tags: data.tags,
        require_all: data.require_all || false,
        amount_sign: data.amount_sign || null,
      });
    }
  }

  // Get expense categories in order
  const expenseNames = config.expensesOrder || Object.keys(config.expenses || {});
  for (const category of expenseNames) {
    const data = config.expenses?.[category];
    if (data) {
      result.push({
        id: crypto.randomUUID(),
        type: "expense",
        category,
        expected: data.expected,
        tags: data.tags,
        require_all: data.require_all || false,
        amount_sign: data.amount_sign || null,
      });
    }
  }

  return result;
}

/**
 * Check if the database has any budget categories at all
 * Used to determine if we need to run initial migration
 */
export async function hasBudgetData(): Promise<boolean> {
  const result = await executeQuery(`
    SELECT COUNT(*) FROM sys_plugin_budget_categories
  `);
  return (result.rows[0]?.[0] as number) > 0;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Helper to get previous month string
 */
export function getPreviousMonth(month: string): string {
  const [year, m] = month.split("-").map(Number);
  const prevDate = new Date(year, m - 2, 1);
  return `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, "0")}`;
}
