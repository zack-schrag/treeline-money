<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { executeQuery, registry } from "../../sdk";
  import { Modal, RowMenu, type RowMenuItem } from "../../shared";
  import type { BudgetCategory, BudgetActual, BudgetType, AmountSign, Transaction, Transfer } from "./types";
  import * as budgetDb from "./db";

  // State
  let categories = $state<BudgetCategory[]>([]);
  let actuals = $state<BudgetActual[]>([]);
  let isLoading = $state(true);
  let error = $state<string | null>(null);

  // Month selection
  let availableMonths = $state<string[]>([]);
  let selectedMonth = $state<string>("");
  let showCopyFromPrevious = $state(false); // Show prompt to copy from previous month
  let copySourceMonth = $state<string | null>(null); // Month to copy from (selected by user)
  let monthsWithData = $state<string[]>([]); // All months that have budget data

  // Current month helper
  function getCurrentMonth(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }
  let isCurrentMonth = $derived(selectedMonth === getCurrentMonth());

  // Account filtering
  let allAccounts = $state<string[]>([]);
  let selectedAccounts = $state<string[]>([]);

  // Navigation
  let cursorIndex = $state(0);
  let containerEl: HTMLDivElement | null = null;

  // Transaction drill-down
  let showTransactions = $state(false);
  let drillDownCategory = $state<BudgetActual | null>(null);
  let drillDownTransactions = $state<Transaction[]>([]);
  let drillDownLoading = $state(false);

  // Row menu state
  let menuOpenForId = $state<string | null>(null);

  function closeMenu() {
    menuOpenForId = null;
  }

  function toggleMenu(id: string, e: MouseEvent) {
    e.stopPropagation();
    menuOpenForId = menuOpenForId === id ? null : id;
  }

  // Editor state
  let isEditing = $state(false);
  let editingCategory = $state<BudgetCategory | null>(null);
  let editorForm = $state({
    type: "expense" as BudgetType,
    category: "",
    expected: 0,
    tags: "",
    require_all: false,
    amount_sign: null as AmountSign | null,
  });

  // Transfer state
  // "incomingTransfers" = transfers TO this month (from previous month's config)
  // "outgoingTransfers" = transfers FROM this month to next month (stored in this month's config)
  let incomingTransfers = $state<Transfer[]>([]);
  let outgoingTransfers = $state<Transfer[]>([]);

  // Reset modal state
  let showResetModal = $state(false);
  let resetSourceMonth = $state<string | null>(null); // Month to copy from when resetting

  // Transfer modal state
  let showTransferModal = $state(false);
  let transferSourceCategory = $state<string>(""); // The category we're transferring FROM
  let transferSourceVariance = $state<number>(0);  // The variance of the source category (for display)
  let transferStorageMonth = $state<string>("");   // The month where transfers are stored (source month)
  let transferTargetCategory = $state<string>(""); // For incoming: the category we're transferring TO (used for remove all)
  let isEditingIncoming = $state(false);           // true if editing incoming transfers (vs outgoing)
  // Modal can have multiple transfer rows
  interface TransferRow {
    id: string;
    toCategory: string;
    amount: number;
  }
  let transferRows = $state<TransferRow[]>([]);
  let isEditingTransfers = $state(false); // true if editing existing transfers, false if creating new

  // All known tags for autocomplete
  let allTags = $state<string[]>([]);

  // Trend data - preloaded for all categories
  interface TrendData {
    month: string;
    actual: number;
  }
  let allCategoryTrends = $state<Map<string, TrendData[]>>(new Map());

  // Current category's trend (looked up from preloaded data)
  let categoryTrend = $derived(currentCategory ? (allCategoryTrends.get(currentCategory.id) || []) : []);

  // Flat list of all actuals for navigation (income first, then budget items)
  let incomeActuals = $derived(actuals.filter(a => a.type === "income"));
  let budgetActuals = $derived(actuals.filter(a => a.type === "expense"));
  let allActuals = $derived([...incomeActuals, ...budgetActuals]);

  let currentActual = $derived(allActuals[cursorIndex]);
  let currentCategory = $derived(categories.find(c => c.id === currentActual?.id));

  // Current category's transfer info for sidebar (aggregated)
  let currentIncomingTransfers = $derived(
    currentActual ? incomingTransfers.filter(t => t.toCategory === currentActual.category) : []
  );
  let currentOutgoingTransfers = $derived(
    currentActual ? outgoingTransfers.filter(t => t.fromCategory === currentActual.category) : []
  );
  // Net incoming amount for the current category (sum of all incoming)
  let currentIncomingNet = $derived(roundToCents(currentIncomingTransfers.reduce((sum, t) => sum + t.amount, 0)));
  // Net outgoing amount (sum of all outgoing from this category)
  let currentOutgoingNet = $derived(roundToCents(currentOutgoingTransfers.reduce((sum, t) => sum + t.amount, 0)));

  // Computed summaries
  let incomeSummary = $derived.by(() => {
    const expected = incomeActuals.reduce((sum, a) => sum + a.expected, 0);
    const actual = incomeActuals.reduce((sum, a) => sum + a.actual, 0);
    const percent = expected > 0 ? Math.floor((actual / expected) * 100) : 0;
    return { expected, actual, percent };
  });

  let budgetSummary = $derived.by(() => {
    const expected = budgetActuals.reduce((sum, a) => sum + a.expected, 0);
    const actual = budgetActuals.reduce((sum, a) => sum + a.actual, 0);
    const percent = expected > 0 ? Math.floor((actual / expected) * 100) : 0;
    return { expected, actual, percent };
  });

  // Remaining = income - budget
  let remainingSummary = $derived.by(() => {
    const expected = incomeSummary.expected - budgetSummary.expected;
    const actual = incomeSummary.actual - budgetSummary.actual;
    const percent = expected > 0 ? Math.floor((actual / expected) * 100) : (actual > 0 ? 100 : 0);
    return { expected, actual, percent };
  });

  // Default template with common categories - used when DB has no data for ANY month
  function getDefaultCategories(): BudgetCategory[] {
    return [
      { id: crypto.randomUUID(), type: "income", category: "Salary", expected: 7000, tags: ["income"], require_all: false, amount_sign: null },
      { id: crypto.randomUUID(), type: "expense", category: "Groceries", expected: 600, tags: ["groceries"], require_all: false, amount_sign: null },
      { id: crypto.randomUUID(), type: "expense", category: "Dining", expected: 300, tags: ["dining", "coffee"], require_all: false, amount_sign: null },
      { id: crypto.randomUUID(), type: "expense", category: "Transportation", expected: 400, tags: ["transportation"], require_all: false, amount_sign: null },
      { id: crypto.randomUUID(), type: "expense", category: "Shopping", expected: 400, tags: ["shopping"], require_all: false, amount_sign: null },
      { id: crypto.randomUUID(), type: "expense", category: "Entertainment", expected: 100, tags: ["entertainment"], require_all: false, amount_sign: null },
      { id: crypto.randomUUID(), type: "expense", category: "Utilities", expected: 250, tags: ["utilities"], require_all: false, amount_sign: null },
      { id: crypto.randomUUID(), type: "expense", category: "Health", expected: 100, tags: ["health"], require_all: false, amount_sign: null },
    ];
  }

  async function saveCategoriesToDb(cats: BudgetCategory[]): Promise<void> {
    if (!selectedMonth) return;
    await budgetDb.saveAllCategories(selectedMonth, cats);
  }

  async function copyFromSourceMonth(): Promise<void> {
    if (!selectedMonth || !copySourceMonth) return;
    try {
      const copiedCategories = await budgetDb.copyFromMonth(copySourceMonth, selectedMonth);
      if (copiedCategories.length > 0) {
        categories = copiedCategories;
        showCopyFromPrevious = false;
        copySourceMonth = null;
        await calculateActuals();
      }
    } catch (e) {
      console.error("Failed to copy from source month:", e);
    }
  }

  /**
   * Find the nearest month that has budget data
   * Prefers more recent months, then falls back to older months
   */
  function findNearestMonth(targetMonth: string, availableMonths: string[]): string | null {
    if (availableMonths.length === 0) return null;

    // Sort by distance from target month, preferring more recent
    const targetDate = new Date(targetMonth + "-01");

    let nearest: string | null = null;
    let nearestDistance = Infinity;

    for (const month of availableMonths) {
      if (month === targetMonth) continue; // Skip the target month itself

      const monthDate = new Date(month + "-01");
      const distance = Math.abs(monthDate.getTime() - targetDate.getTime());
      const isMoreRecent = monthDate > targetDate;

      // Prefer more recent months by giving them a slight advantage
      const adjustedDistance = isMoreRecent ? distance * 0.9 : distance;

      if (adjustedDistance < nearestDistance) {
        nearestDistance = adjustedDistance;
        nearest = month;
      }
    }

    return nearest;
  }

  async function startFresh(): Promise<void> {
    // User declined copy from previous - start with defaults for this month
    if (!selectedMonth) return;
    const defaults = getDefaultCategories();
    await budgetDb.saveAllCategories(selectedMonth, defaults);
    categories = defaults;
    showCopyFromPrevious = false;
    copySourceMonth = null;
    await calculateActuals();
  }

  async function openResetModal(): Promise<void> {
    // Load months with data for the dropdown
    monthsWithData = await budgetDb.getMonthsWithData();
    const otherMonths = monthsWithData.filter(m => m !== selectedMonth);
    // Default to previous month if it has data, otherwise nearest
    const prevMonth = budgetDb.getPreviousMonth(selectedMonth);
    resetSourceMonth = otherMonths.includes(prevMonth) ? prevMonth : findNearestMonth(selectedMonth, otherMonths);
    showResetModal = true;
  }

  function closeResetModal(): void {
    showResetModal = false;
    resetSourceMonth = null;
  }

  async function resetFromMonth(): Promise<void> {
    if (!selectedMonth || !resetSourceMonth) return;
    try {
      const copiedCategories = await budgetDb.copyFromMonth(resetSourceMonth, selectedMonth);
      // Also clear any existing rollovers from this month
      await budgetDb.deleteMonthRollovers(selectedMonth);
      categories = copiedCategories;
      outgoingTransfers = [];
      closeResetModal();
      await calculateActuals();
      await loadAllTrends();
    } catch (e) {
      console.error("Failed to reset from month:", e);
    }
  }

  async function deleteBudget(): Promise<void> {
    if (!selectedMonth) return;
    // Delete all categories for this month
    await budgetDb.saveAllCategories(selectedMonth, []);
    // Delete any rollovers from this month
    await budgetDb.deleteMonthRollovers(selectedMonth);
    categories = [];
    outgoingTransfers = [];
    closeResetModal();
    // This will trigger the "no budget" state
    await loadCategories();
  }

  async function loadAllAccounts() {
    const result = await executeQuery(`SELECT DISTINCT account_name FROM transactions WHERE account_name IS NOT NULL AND account_name != '' ORDER BY account_name`);
    allAccounts = result.rows.map(r => r[0] as string);
  }

  async function loadAllTags() {
    const result = await executeQuery(`SELECT DISTINCT unnest(tags) as tag FROM transactions WHERE tags != [] ORDER BY tag`);
    allTags = result.rows.map(r => r[0] as string);
  }

  async function loadCategoriesFromDb() {
    if (!selectedMonth) return;

    try {
      // Load from database - each month is self-contained
      const monthData = await budgetDb.loadMonthData(selectedMonth);

      if (monthData.categories.length === 0) {
        // Check what months have budget data
        monthsWithData = await budgetDb.getMonthsWithData();
        const otherMonths = monthsWithData.filter(m => m !== selectedMonth);

        if (otherMonths.length === 0) {
          // First time setup - create defaults for this month
          const defaults = getDefaultCategories();
          await budgetDb.saveAllCategories(selectedMonth, defaults);
          categories = defaults;
          showCopyFromPrevious = false;
          copySourceMonth = null;
        } else {
          // No categories for this month but other months have data
          // Default to nearest month, user can change via dropdown
          categories = [];
          copySourceMonth = findNearestMonth(selectedMonth, otherMonths);
          showCopyFromPrevious = true;
        }
      } else {
        categories = monthData.categories;
        showCopyFromPrevious = false;
        copySourceMonth = null;
        monthsWithData = [];
      }

      outgoingTransfers = monthData.outgoingRollovers;
      incomingTransfers = monthData.incomingRollovers;
    } catch (e) {
      console.error("Failed to load categories:", e);
      categories = [];
    }
  }

  // Alias for compatibility with existing code
  async function loadCategories() {
    await loadCategoriesFromDb();
  }

  function buildAccountFilter(): string {
    if (selectedAccounts.length === 0) return "";
    return `AND account_name IN (${selectedAccounts.map(a => `'${a.replace(/'/g, "''")}'`).join(", ")})`;
  }

  async function calculateActualsForMonth(month: string): Promise<BudgetActual[]> {
    if (!month || categories.length === 0) return [];

    const accountFilter = buildAccountFilter();
    const subqueries = categories.map(cat => {
      const defaultSign = cat.type === "income" ? "positive" : "negative";
      const effectiveSign = cat.amount_sign || defaultSign;
      let tagCondition = cat.require_all
        ? cat.tags.map(t => `list_contains(tags, '${t.replace(/'/g, "''")}')`).join(" AND ")
        : `list_has_any(tags, [${cat.tags.map(t => `'${t.replace(/'/g, "''")}'`).join(", ")}])`;
      let amountCondition = effectiveSign === "positive" ? "AND amount > 0" : effectiveSign === "negative" ? "AND amount < 0" : "";
      return `SELECT '${cat.id}' as id, COALESCE(SUM(ABS(amount)), 0) as total FROM transactions WHERE strftime('%Y-%m', transaction_date) = '${month}' AND ${tagCondition} ${amountCondition} ${accountFilter}`;
    });

    try {
      const result = await executeQuery(subqueries.join(" UNION ALL "));
      const totalsById = new Map<string, number>();
      for (const row of result.rows) totalsById.set(row[0] as string, row[1] as number);

      return categories.map(cat => {
        const actual = totalsById.get(cat.id) || 0;
        const variance = cat.type === "income" ? actual - cat.expected : cat.expected - actual;
        const percentUsed = cat.expected > 0 ? Math.floor((actual / cat.expected) * 100) : (actual > 0 ? 100 : 0);
        return { id: cat.id, type: cat.type, category: cat.category, expected: cat.expected, actual, variance, percentUsed };
      });
    } catch (e) {
      console.error("Failed to calculate actuals:", e);
      return [];
    }
  }

  async function calculateActuals() {
    actuals = await calculateActualsForMonth(selectedMonth);
  }

  async function loadAllTrends() {
    if (categories.length === 0) {
      allCategoryTrends = new Map();
      return;
    }

    const accountFilter = buildAccountFilter();

    // Build a single query that gets 6-month trends for ALL categories
    // Each subquery wrapped in parentheses to make LIMIT work
    const subqueries = categories.map(cat => {
      const defaultSign = cat.type === "income" ? "positive" : "negative";
      const effectiveSign = cat.amount_sign || defaultSign;
      const tagCondition = cat.require_all
        ? cat.tags.map(t => `list_contains(tags, '${t.replace(/'/g, "''")}')`).join(" AND ")
        : `list_has_any(tags, [${cat.tags.map(t => `'${t.replace(/'/g, "''")}'`).join(", ")}])`;
      const amountCondition = effectiveSign === "positive" ? "AND amount > 0" : effectiveSign === "negative" ? "AND amount < 0" : "";

      return `(SELECT '${cat.id}' as category_id, strftime('%Y-%m', transaction_date) as month, COALESCE(SUM(ABS(amount)), 0) as total
        FROM transactions
        WHERE ${tagCondition} ${amountCondition} ${accountFilter}
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6)`;
    });

    try {
      const query = subqueries.join(" UNION ALL ");
      const result = await executeQuery(query);

      // Group results by category
      const trendsMap = new Map<string, TrendData[]>();
      for (const row of result.rows) {
        const categoryId = row[0] as string;
        const month = row[1] as string;
        const total = row[2] as number;

        if (!trendsMap.has(categoryId)) {
          trendsMap.set(categoryId, []);
        }
        trendsMap.get(categoryId)!.push({ month, actual: total });
      }

      // Sort each category's trends by month (oldest first for display)
      for (const [id, trends] of trendsMap) {
        trends.sort((a, b) => a.month.localeCompare(b.month));
      }

      allCategoryTrends = trendsMap;
    } catch (e) {
      console.error("Failed to load trends:", e);
      allCategoryTrends = new Map();
    }
  }

  let initialLoadComplete = false;

  async function loadAll() {
    isLoading = true;
    error = null;
    try {
      // Load months first but don't set selectedMonth yet to avoid triggering effect
      const result = await executeQuery(`SELECT DISTINCT strftime('%Y-%m', transaction_date) as month FROM transactions ORDER BY month DESC`);
      const transactionMonths = result.rows.map(r => r[0] as string);
      const now = new Date();
      const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
      const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
      const nextMonthStr = `${nextMonth.getFullYear()}-${String(nextMonth.getMonth() + 1).padStart(2, '0')}`;
      const allMonths = new Set([nextMonthStr, currentMonth, ...transactionMonths]);
      availableMonths = Array.from(allMonths).sort().reverse();
      // Default to current month, not the next month
      const targetMonth = currentMonth;

      // Load other data in parallel
      await Promise.all([loadAllTags(), loadAllAccounts()]);

      // Now load categories for the target month and set selectedMonth
      selectedMonth = targetMonth;
      await loadCategories();
      await Promise.all([calculateActuals(), loadAllTrends()]);

      initialLoadComplete = true;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load budget data";
    } finally {
      isLoading = false;
    }
  }

  async function loadTransactionsForCategory(cat: BudgetActual) {
    drillDownCategory = cat;
    drillDownLoading = true;
    showTransactions = true;

    const category = categories.find(c => c.id === cat.id);
    if (!category) { drillDownLoading = false; return; }

    const accountFilter = buildAccountFilter();
    const defaultSign = category.type === "income" ? "positive" : "negative";
    const effectiveSign = category.amount_sign || defaultSign;
    let tagCondition = category.require_all
      ? category.tags.map(t => `list_contains(tags, '${t.replace(/'/g, "''")}')`).join(" AND ")
      : `list_has_any(tags, [${category.tags.map(t => `'${t.replace(/'/g, "''")}'`).join(", ")}])`;
    let amountCondition = effectiveSign === "positive" ? "AND amount > 0" : effectiveSign === "negative" ? "AND amount < 0" : "";

    try {
      const result = await executeQuery(`SELECT transaction_id, transaction_date, description, amount, tags, account_name FROM transactions WHERE strftime('%Y-%m', transaction_date) = '${selectedMonth}' AND ${tagCondition} ${amountCondition} ${accountFilter} ORDER BY transaction_date DESC`);
      drillDownTransactions = result.rows.map(row => ({ transaction_id: row[0] as string, transaction_date: row[1] as string, description: row[2] as string, amount: row[3] as number, tags: (row[4] as string[]) || [], account_name: row[5] as string }));
    } catch (e) {
      drillDownTransactions = [];
    } finally {
      drillDownLoading = false;
    }
  }

  function closeDrillDown() {
    showTransactions = false;
    drillDownCategory = null;
    drillDownTransactions = [];
    containerEl?.focus();
  }

  function handleModalEdit() {
    const cat = categories.find(c => c.id === drillDownCategory?.id);
    closeDrillDown();
    if (cat) startEditCategory(cat);
  }

  function handleModalDelete() {
    const cat = categories.find(c => c.id === drillDownCategory?.id);
    closeDrillDown();
    if (cat) deleteCategory(cat);
  }

  function startAddCategory(type: BudgetType) {
    editingCategory = null;
    editorForm = { type, category: "", expected: 0, tags: "", require_all: false, amount_sign: null };
    isEditing = true;
  }

  function startEditCategory(cat: BudgetCategory) {
    editingCategory = cat;
    editorForm = { type: cat.type, category: cat.category, expected: cat.expected, tags: cat.tags.join(", "), require_all: cat.require_all, amount_sign: cat.amount_sign };
    isEditing = true;
  }

  function cancelEdit() {
    isEditing = false;
    editingCategory = null;
    containerEl?.focus();
  }

  async function saveCategory() {
    const tags = editorForm.tags.split(",").map(t => t.trim()).filter(t => t);
    if (!editorForm.category.trim() || tags.length === 0 || !selectedMonth) return;

    // Use existing ID if editing, otherwise generate new UUID
    const categoryId = editingCategory?.id ?? crypto.randomUUID();
    const newCategory: BudgetCategory = { id: categoryId, type: editorForm.type, category: editorForm.category.trim(), expected: editorForm.expected, tags, require_all: editorForm.require_all, amount_sign: editorForm.amount_sign };

    let updatedCategories: BudgetCategory[];
    if (editingCategory) {
      // Replace in place to preserve position
      updatedCategories = categories.map(c => c.id === editingCategory.id ? newCategory : c);
    } else {
      // New category - append to end
      updatedCategories = [...categories, newCategory];
    }

    // Save to database for this month
    await budgetDb.saveAllCategories(selectedMonth, updatedCategories);
    cancelEdit();
    await loadCategories();
    await calculateActuals();
  }

  async function deleteCategory(cat: BudgetCategory) {
    if (!selectedMonth) return;
    const updatedCategories = categories.filter(c => c.id !== cat.id);
    await budgetDb.saveAllCategories(selectedMonth, updatedCategories);
    await loadCategories();
    await Promise.all([calculateActuals(), loadAllTrends()]);
  }

  function formatCurrency(amount: number): string {
    return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  // Helper to round to cents (2 decimal places) - fixes floating point errors
  function roundToCents(amount: number): number {
    return Math.round(amount * 100) / 100;
  }

  function formatAmount(amount: number): string {
    return Math.abs(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Format "2025-12" as "Dec 2025"
  function formatMonth(monthStr: string): string {
    if (!monthStr) return "—";
    const [year, month] = monthStr.split("-");
    const date = new Date(parseInt(year), parseInt(month) - 1, 1);
    return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  }

  // Format "2025-12" as "Dec" (short month only, for trends)
  function formatMonthShort(monthStr: string): string {
    if (!monthStr) return "";
    const [year, month] = monthStr.split("-");
    const date = new Date(parseInt(year), parseInt(month) - 1, 1);
    return date.toLocaleDateString("en-US", { month: "short" });
  }

  function getStatusColor(actual: BudgetActual): string {
    if (actual.type === "income") return actual.percentUsed >= 100 ? "var(--accent-success, #22c55e)" : "var(--text-muted)";
    if (actual.percentUsed > 100) return "var(--accent-danger, #ef4444)";
    if (actual.percentUsed > 90) return "var(--accent-warning, #f59e0b)";
    return "var(--accent-success, #22c55e)";
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (isEditing || showTransactions || showTransferModal) return;

    // Cmd/Ctrl + Arrow for reordering
    if ((e.metaKey || e.ctrlKey) && (e.key === "ArrowUp" || e.key === "ArrowDown")) {
      e.preventDefault();
      moveCategory(e.key === "ArrowUp" ? "up" : "down");
      return;
    }

    switch(e.key) {
      case "j":
      case "ArrowDown":
        e.preventDefault();
        if (cursorIndex < allActuals.length - 1) cursorIndex++;
        scrollToCursor();
        break;
      case "k":
      case "ArrowUp":
        e.preventDefault();
        if (cursorIndex > 0) cursorIndex--;
        scrollToCursor();
        break;
      case "Enter":
        e.preventDefault();
        if (currentActual) loadTransactionsForCategory(currentActual);
        break;
      case "e":
        e.preventDefault();
        if (currentCategory) startEditCategory(currentCategory);
        break;
      case "d":
        e.preventDefault();
        if (currentCategory) deleteCategory(currentCategory);
        break;
      case "a":
        e.preventDefault();
        startAddCategory("expense");
        break;
      case "h":
      case "ArrowLeft":
        e.preventDefault();
        cycleMonth(1);
        break;
      case "l":
      case "ArrowRight":
        e.preventDefault();
        cycleMonth(-1);
        break;
      case "g":
        e.preventDefault();
        cursorIndex = 0;
        scrollToCursor();
        break;
      case "G":
        e.preventDefault();
        cursorIndex = allActuals.length - 1;
        scrollToCursor();
        break;
      case "t":
        e.preventDefault();
        goToCurrentMonth();
        break;
    }
  }

  function cycleMonth(delta: number) {
    const idx = availableMonths.indexOf(selectedMonth);
    const newIdx = idx + delta;
    if (newIdx >= 0 && newIdx < availableMonths.length) {
      selectedMonth = availableMonths[newIdx];
    }
  }

  function goToCurrentMonth() {
    selectedMonth = getCurrentMonth();
  }

  // Get next month string
  function getNextMonth(month: string): string {
    const [year, m] = month.split("-").map(Number);
    const nextDate = new Date(year, m, 1); // m is already 1-indexed, so this gives next month
    return `${nextDate.getFullYear()}-${String(nextDate.getMonth() + 1).padStart(2, '0')}`;
  }

  // Get previous month string
  function getPrevMonth(month: string): string {
    const [year, m] = month.split("-").map(Number);
    const prevDate = new Date(year, m - 2, 1); // m is 1-indexed, so m-2 gives previous month
    return `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`;
  }

  // Transfer functions
  // Generate a unique ID for a new transfer
  function generateTransferId(): string {
    return `transfer-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }

  // Open modal to create/edit outgoing transfers from a category (current month → next month)
  function openTransferModal(actual: BudgetActual, e: MouseEvent) {
    e.stopPropagation();
    transferSourceCategory = actual.category;
    transferSourceVariance = roundToCents(actual.variance);
    transferStorageMonth = selectedMonth; // Outgoing transfers are stored in current month
    transferTargetCategory = ""; // Not used for outgoing
    isEditingIncoming = false;
    isEditingTransfers = false;

    // Check if there are existing outgoing transfers from this category
    const existingTransfers = outgoingTransfers.filter(t => t.fromCategory === actual.category);
    if (existingTransfers.length > 0) {
      // Editing existing transfers
      isEditingTransfers = true;
      transferRows = existingTransfers.map(t => ({
        id: t.id,
        toCategory: t.toCategory,
        amount: roundToCents(t.amount),
      }));
    } else {
      // New transfer - default to same category (simple rollover)
      transferRows = [{
        id: generateTransferId(),
        toCategory: actual.category,
        amount: roundToCents(actual.variance),
      }];
    }

    showTransferModal = true;
  }

  // Open modal to edit incoming transfers (transfers TO current month, stored in previous month)
  function openEditIncomingTransfers(categoryName: string, e: MouseEvent) {
    e.stopPropagation();
    // Incoming transfers are stored in the previous month's config
    const transfers = incomingTransfers.filter(t => t.toCategory === categoryName);
    if (transfers.length === 0) return;

    // Get the source category (might be different categories)
    const sourceCategories = [...new Set(transfers.map(t => t.fromCategory))];
    transferSourceCategory = sourceCategories[0]; // Primary source (for display)
    transferSourceVariance = 0; // Not relevant for editing incoming
    transferStorageMonth = getPrevMonth(selectedMonth); // Incoming transfers are stored in previous month
    transferTargetCategory = categoryName; // The category receiving transfers (for remove all)
    isEditingIncoming = true;
    isEditingTransfers = true;

    transferRows = transfers.map(t => ({
      id: t.id,
      toCategory: t.toCategory,
      amount: roundToCents(t.amount),
    }));

    showTransferModal = true;
  }

  function closeTransferModal() {
    showTransferModal = false;
    transferSourceCategory = "";
    transferSourceVariance = 0;
    transferStorageMonth = "";
    transferTargetCategory = "";
    isEditingIncoming = false;
    transferRows = [];
    isEditingTransfers = false;
    containerEl?.focus();
  }

  function addTransferRow() {
    transferRows = [...transferRows, {
      id: generateTransferId(),
      toCategory: transferSourceCategory, // Default to same category
      amount: 0,
    }];
  }

  function removeTransferRow(id: string) {
    transferRows = transferRows.filter(r => r.id !== id);
  }

  // Get available categories for transfer destination
  let availableTransferCategories = $derived(
    budgetActuals.map(a => a.category)
  );

  // Compute total allocated and remaining
  let totalAllocated = $derived(transferRows.reduce((sum, r) => sum + (r.amount || 0), 0));
  let remainingToAllocate = $derived(transferSourceVariance - totalAllocated);

  async function saveTransfers() {
    if (!transferSourceCategory || !transferStorageMonth) return;

    // Determine target month for rollovers
    const toMonth = getNextMonth(transferStorageMonth);

    // Load existing rollovers from this source month
    const existingRollovers = await budgetDb.loadOutgoingRollovers(transferStorageMonth);

    // Remove any existing rollovers from this source category
    const otherRollovers = existingRollovers.filter(t => t.fromCategory !== transferSourceCategory);

    // Add the new rollovers (filter out zero amounts)
    const newRollovers: Transfer[] = transferRows
      .filter(r => r.amount !== 0)
      .map(r => ({
        id: r.id,
        fromCategory: transferSourceCategory,
        toCategory: r.toCategory,
        amount: roundToCents(r.amount),
      }));

    // Save all rollovers for this source month
    const allRollovers = [...otherRollovers, ...newRollovers];
    await budgetDb.saveMonthRollovers(transferStorageMonth, toMonth, allRollovers);

    await loadCategories();
    closeTransferModal();
  }

  async function removeAllTransfers() {
    if (!transferStorageMonth) return;

    // Load existing rollovers from this source month
    const existingRollovers = await budgetDb.loadOutgoingRollovers(transferStorageMonth);
    const toMonth = getNextMonth(transferStorageMonth);

    let remainingRollovers: Transfer[];
    if (isEditingIncoming) {
      // Remove all rollovers TO the target category
      if (!transferTargetCategory) return;
      remainingRollovers = existingRollovers.filter(t => t.toCategory !== transferTargetCategory);
    } else {
      // Remove all rollovers FROM the source category
      if (!transferSourceCategory) return;
      remainingRollovers = existingRollovers.filter(t => t.fromCategory !== transferSourceCategory);
    }

    await budgetDb.saveMonthRollovers(transferStorageMonth, toMonth, remainingRollovers);

    await loadCategories();
    closeTransferModal();
  }

  function scrollToCursor() {
    setTimeout(() => {
      document.querySelector(`[data-index="${cursorIndex}"]`)?.scrollIntoView({ block: "nearest" });
    }, 0);
  }

  function handleRowClick(index: number) {
    cursorIndex = index;
    containerEl?.focus();
  }

  function handleRowDoubleClick(index: number) {
    // Get the actual for this index
    const actual = index < incomeActuals.length
      ? incomeActuals[index]
      : budgetActuals[index - incomeActuals.length];
    if (actual) {
      loadTransactionsForCategory(actual);
    }
  }

  // Move category up or down within its section
  async function moveCategory(direction: "up" | "down") {
    if (!currentCategory) return;

    const type = currentCategory.type;
    const typeCats = [...categories.filter(c => c.type === type)];
    const currentIndex = typeCats.findIndex(c => c.id === currentCategory.id);

    if (currentIndex === -1) return;

    const newIndex = direction === "up" ? currentIndex - 1 : currentIndex + 1;
    if (newIndex < 0 || newIndex >= typeCats.length) return;

    // Swap positions
    [typeCats[currentIndex], typeCats[newIndex]] = [typeCats[newIndex], typeCats[currentIndex]];

    // Rebuild categories array (income first, then expenses)
    const incomeCats = type === "income" ? typeCats : categories.filter(c => c.type === "income");
    const expenseCats = type === "expense" ? typeCats : categories.filter(c => c.type === "expense");
    const newCategories = [...incomeCats, ...expenseCats];

    // Save and update
    if (!selectedMonth) return;
    await budgetDb.saveAllCategories(selectedMonth, newCategories);
    categories = newCategories;
    await calculateActuals();

    // Move cursor to follow the category
    cursorIndex = cursorIndex + (direction === "up" ? -1 : 1);
  }

  $effect(() => {
    if (selectedMonth && initialLoadComplete) {
      // Reload config for the new month (may have month-specific budget)
      loadCategories().then(() => Promise.all([calculateActuals(), loadAllTrends()]));
    }
  });


  // Subscribe to global refresh events
  let unsubscribeRefresh: (() => void) | null = null;

  onMount(async () => {
    await loadAll();
    // Focus container for keyboard navigation
    containerEl?.focus();

    // Listen for data refresh events (e.g., demo mode toggle)
    unsubscribeRefresh = registry.on("data:refresh", () => {
      loadAll();
    });
  });

  onDestroy(() => {
    unsubscribeRefresh?.();
  });
</script>

<div class="budget-view" bind:this={containerEl} tabindex="0" onkeydown={handleKeyDown}>
  <!-- Header -->
  <div class="header">
    <div class="title-row">
      <h1 class="title">Budget</h1>
      <div class="month-nav">
        <button class="nav-btn" onclick={() => cycleMonth(1)} disabled={availableMonths.indexOf(selectedMonth) === availableMonths.length - 1}>←</button>
        <span class="current-month">
          {formatMonth(selectedMonth)}
        </span>
        <button class="nav-btn" onclick={() => cycleMonth(-1)} disabled={availableMonths.indexOf(selectedMonth) === 0}>→</button>
        <button class="this-month-btn" onclick={goToCurrentMonth} title="Jump to current month" disabled={isCurrentMonth}>This Month</button>
        <button class="reset-btn" onclick={openResetModal} title="Reset or delete this month's budget" disabled={showCopyFromPrevious}>Reset</button>
      </div>
    </div>
  </div>

  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  <div class="main-content">
    <!-- Category list -->
    <div class="list-container">
      {#if isLoading}
        <div class="empty-state">Loading...</div>
      {:else if showCopyFromPrevious}
        <div class="copy-from-previous">
          <div class="copy-prompt">
            <p>No budget configured for <strong>{formatMonth(selectedMonth)}</strong></p>
            {#if monthsWithData.filter(m => m !== selectedMonth).length > 0}
              <p class="copy-hint">Copy categories from an existing month?</p>
            {:else}
              <p class="copy-hint">Start with default categories?</p>
            {/if}
          </div>
          <div class="copy-actions">
            {#if monthsWithData.filter(m => m !== selectedMonth).length > 0}
              <div class="copy-select-row">
                <select class="copy-month-select" bind:value={copySourceMonth}>
                  {#each monthsWithData.filter(m => m !== selectedMonth) as month}
                    <option value={month}>{formatMonth(month)}</option>
                  {/each}
                </select>
                <button class="btn primary" onclick={copyFromSourceMonth} disabled={!copySourceMonth}>Copy</button>
              </div>
            {/if}
            <button class="btn secondary" onclick={startFresh}>Start fresh</button>
          </div>
        </div>
      {:else if allActuals.length === 0}
        <div class="empty-state">No budget categories. Press <kbd>a</kbd> to add one.</div>
      {:else}
        <!-- Income Section -->
        <div class="section">
          <div class="section-header income-header">
            <div class="row-name section-title">INCOME</div>
            <div class="row-bar"></div>
            <div class="row-actual">{formatCurrency(incomeSummary.actual)}</div>
            <div class="row-expected">/ {formatCurrency(incomeSummary.expected)}</div>
            <div class="row-percent" style="color: {incomeSummary.percent >= 100 ? 'var(--accent-success, #22c55e)' : 'var(--text-muted)'}">{incomeSummary.percent}%</div>
            <div class="transfer-btn-placeholder"></div>
            <div class="row-details-placeholder"></div>
          </div>
          {#each incomeActuals as actual, i}
            {@const globalIndex = i}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
              class="row"
              class:cursor={cursorIndex === globalIndex}
              data-index={globalIndex}
              onclick={() => handleRowClick(globalIndex)}
              ondblclick={() => handleRowDoubleClick(globalIndex)}
              role="listitem"
            >
              <div class="row-name">{actual.category}</div>
              <div class="row-bar">
                <div class="bar-bg"><div class="bar-fill" style="width: {Math.min(actual.percentUsed, 100)}%; background: {actual.percentUsed >= 100 ? 'var(--accent-success, #22c55e)' : 'var(--accent-primary)'}"></div></div>
              </div>
              <div class="row-actual">{formatCurrency(actual.actual)}</div>
              <div class="row-expected">/ {formatCurrency(actual.expected)}</div>
              <div class="row-percent" style="color: {actual.percentUsed >= 100 ? 'var(--accent-success, #22c55e)' : 'var(--text-muted)'}">{actual.percentUsed}%</div>
              <div class="transfer-btn-placeholder"></div>
              <RowMenu
                items={[
                  { label: "View", action: () => { loadTransactionsForCategory(actual); closeMenu(); } },
                  { label: "Edit", action: () => { const cat = categories.find(c => c.id === actual.id); if (cat) startEditCategory(cat); closeMenu(); } },
                  { label: "Delete", action: () => { const cat = categories.find(c => c.id === actual.id); if (cat) deleteCategory(cat); closeMenu(); }, danger: true },
                ]}
                isOpen={menuOpenForId === actual.id}
                onToggle={(e) => toggleMenu(actual.id, e)}
                onClose={closeMenu}
              />
            </div>
          {/each}
          <button class="add-row" onclick={() => startAddCategory("income")}>+ Add income</button>
        </div>

        <!-- Section Divider -->
        <div class="section-divider"></div>

        <!-- Budget Section -->
        <div class="section">
          <div class="section-header budget-header">
            <div class="row-name section-title">BUDGET</div>
            <div class="row-bar"></div>
            <div class="row-actual">{formatCurrency(budgetSummary.actual)}</div>
            <div class="row-expected">/ {formatCurrency(budgetSummary.expected)}</div>
            <div class="row-percent" style="color: {budgetSummary.percent > 100 ? 'var(--accent-danger, #ef4444)' : budgetSummary.percent > 90 ? 'var(--accent-warning, #f59e0b)' : 'var(--accent-success, #22c55e)'}">{budgetSummary.percent}%</div>
            <div class="transfer-btn-placeholder"></div>
            <div class="row-details-placeholder"></div>
          </div>
          {#each budgetActuals as actual, i}
            {@const globalIndex = incomeActuals.length + i}
            {@const incoming = incomingTransfers.filter(t => t.toCategory === actual.category)}
            {@const incomingNet = roundToCents(incoming.reduce((sum, t) => sum + t.amount, 0))}
            {@const outgoing = outgoingTransfers.filter(t => t.fromCategory === actual.category)}
            {@const outgoingNet = roundToCents(outgoing.reduce((sum, t) => sum + t.amount, 0))}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
              class="row"
              class:cursor={cursorIndex === globalIndex}
              data-index={globalIndex}
              onclick={() => handleRowClick(globalIndex)}
              ondblclick={() => handleRowDoubleClick(globalIndex)}
              role="listitem"
            >
              <div class="row-name">
                {#if incomingNet !== 0}
                  <button
                    class="transfer-badge incoming"
                    class:positive={incomingNet >= 0}
                    class:negative={incomingNet < 0}
                    title="Click to view incoming transfers"
                    onclick={(e) => openEditIncomingTransfers(actual.category, e)}
                  >
                    {incomingNet >= 0 ? '+' : ''}{formatCurrency(incomingNet)}
                  </button>
                {/if}
                {actual.category}
                {#if outgoingNet !== 0}
                  <span
                    class="transfer-badge outgoing"
                    class:positive={outgoingNet >= 0}
                    class:negative={outgoingNet < 0}
                    title="Transferred to {formatMonth(getNextMonth(selectedMonth))}"
                  >
                    → {outgoingNet >= 0 ? '+' : ''}{formatCurrency(outgoingNet)}
                  </span>
                {/if}
              </div>
              <div class="row-bar">
                <div class="bar-bg"><div class="bar-fill" style="width: {Math.min(actual.percentUsed, 100)}%; background: {getStatusColor(actual)}"></div></div>
              </div>
              <div class="row-actual">{formatCurrency(actual.actual)}</div>
              <div class="row-expected">/ {formatCurrency(actual.expected + incomingNet)}</div>
              <div class="row-percent" style="color: {getStatusColor(actual)}">{actual.percentUsed}%</div>
              <button
                class="transfer-btn"
                class:has-outgoing={outgoing.length > 0}
                onclick={(e) => openTransferModal(actual, e)}
                title={outgoing.length > 0 ? `Edit transfers to ${formatMonth(getNextMonth(selectedMonth))}` : "Transfer to next month"}
              >→</button>
              <RowMenu
                items={[
                  { label: "View", action: () => { loadTransactionsForCategory(actual); closeMenu(); } },
                  { label: "Edit", action: () => { const cat = categories.find(c => c.id === actual.id); if (cat) startEditCategory(cat); closeMenu(); } },
                  { label: "Delete", action: () => { const cat = categories.find(c => c.id === actual.id); if (cat) deleteCategory(cat); closeMenu(); }, danger: true },
                ]}
                isOpen={menuOpenForId === actual.id}
                onToggle={(e) => toggleMenu(actual.id, e)}
                onClose={closeMenu}
              />
            </div>
          {/each}
          <button class="add-row" onclick={() => startAddCategory("expense")}>+ Add category</button>
        </div>

        <!-- Remaining Row -->
        <div class="remaining-row">
          <div class="row-name remaining-label">REMAINING</div>
          <div class="row-bar">
            <div class="bar-bg"><div class="bar-fill" style="width: {Math.min(Math.max(remainingSummary.percent, 0), 100)}%; background: {remainingSummary.actual >= 0 ? 'var(--accent-success, #22c55e)' : 'var(--accent-danger, #ef4444)'}"></div></div>
          </div>
          <div class="row-actual" style="color: {remainingSummary.actual >= 0 ? 'var(--accent-success, #22c55e)' : 'var(--accent-danger, #ef4444)'}">{formatCurrency(remainingSummary.actual)}</div>
          <div class="row-expected">/ {formatCurrency(remainingSummary.expected)}</div>
          <div class="row-percent" style="color: {remainingSummary.actual >= remainingSummary.expected ? 'var(--accent-success, #22c55e)' : 'var(--text-muted)'}">{remainingSummary.percent}%</div>
          <div class="transfer-btn-placeholder"></div>
          <div class="row-details-placeholder"></div>
        </div>
      {/if}
    </div>

    <!-- Sidebar -->
    <div class="sidebar">
      {#if currentActual && currentCategory}
        <div class="sidebar-section">
          <div class="sidebar-title">Selected</div>
          <div class="detail-name">{currentActual.category}</div>
          <div class="detail-type">{currentActual.type}</div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">Tags</div>
          <div class="tag-list">
            {#each currentCategory.tags as tag}
              <span class="tag">{tag}</span>
            {/each}
          </div>
          {#if currentCategory.require_all}
            <div class="tag-mode">Requires ALL tags</div>
          {/if}
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">Progress</div>
          <div class="detail-row">
            <span>Actual:</span>
            <span class="mono">{formatCurrency(currentActual.actual)}</span>
          </div>
          <div class="detail-row">
            <span>Expected:</span>
            <span class="mono">{formatCurrency(currentActual.expected)}</span>
          </div>
          <div class="detail-row">
            <span>Variance:</span>
            <span class="mono" class:positive={currentActual.variance >= 0} class:negative={currentActual.variance < 0}>{formatCurrency(currentActual.variance)}</span>
          </div>
        </div>

        {#if currentIncomingTransfers.length > 0 || currentOutgoingTransfers.length > 0}
          <div class="sidebar-section">
            <div class="sidebar-title">Transfers</div>
            {#if currentIncomingTransfers.length > 0}
              <div class="transfer-group incoming">
                <div class="transfer-group-label">Incoming</div>
                {#each currentIncomingTransfers as transfer}
                  <div class="transfer-detail">
                    <span class="transfer-from">from {transfer.fromCategory}</span>
                    <span class="transfer-amount" class:positive={transfer.amount >= 0} class:negative={transfer.amount < 0}>
                      {transfer.amount >= 0 ? '+' : ''}{formatCurrency(transfer.amount)}
                    </span>
                  </div>
                {/each}
                {#if currentIncomingTransfers.length > 1}
                  <div class="transfer-total">
                    <span>Total:</span>
                    <span class="transfer-amount" class:positive={currentIncomingNet >= 0} class:negative={currentIncomingNet < 0}>
                      {currentIncomingNet >= 0 ? '+' : ''}{formatCurrency(currentIncomingNet)}
                    </span>
                  </div>
                {/if}
              </div>
            {/if}
            {#if currentOutgoingTransfers.length > 0}
              <div class="transfer-group outgoing">
                <div class="transfer-group-label">To {formatMonth(getNextMonth(selectedMonth))}</div>
                {#each currentOutgoingTransfers as transfer}
                  <div class="transfer-detail">
                    <span class="transfer-to">→ {transfer.toCategory}</span>
                    <span class="transfer-amount" class:positive={transfer.amount >= 0} class:negative={transfer.amount < 0}>
                      {transfer.amount >= 0 ? '+' : ''}{formatCurrency(transfer.amount)}
                    </span>
                  </div>
                {/each}
                {#if currentOutgoingTransfers.length > 1}
                  <div class="transfer-total">
                    <span>Total:</span>
                    <span class="transfer-amount" class:positive={currentOutgoingNet >= 0} class:negative={currentOutgoingNet < 0}>
                      {currentOutgoingNet >= 0 ? '+' : ''}{formatCurrency(currentOutgoingNet)}
                    </span>
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {/if}

        <div class="sidebar-section">
          <div class="sidebar-title">6-Month Trend</div>
          {#if categoryTrend.length === 0}
            <div class="trend-empty">No history</div>
          {:else}
            {@const maxActual = Math.max(...categoryTrend.map(t => t.actual), 1)}
            {@const avgActual = categoryTrend.reduce((sum, t) => sum + t.actual, 0) / categoryTrend.length}
            <div class="trend-chart">
              {#each categoryTrend as trend}
                <div class="trend-row">
                  <span class="trend-month">{formatMonthShort(trend.month)}</span>
                  <div class="trend-bar-container">
                    <div class="trend-bar" style="width: {(trend.actual / maxActual) * 100}%"></div>
                  </div>
                  <span class="trend-amount">{formatCurrency(trend.actual)}</span>
                </div>
              {/each}
            </div>
            <div class="trend-avg">Avg: {formatCurrency(avgActual)}</div>
          {/if}
        </div>
      {:else}
        <div class="sidebar-empty">Select a category</div>
      {/if}
    </div>
  </div>

  <!-- Keyboard shortcuts footer -->
  <div class="shortcuts-footer">
    <span class="shortcut"><kbd>j</kbd><kbd>k</kbd> nav</span>
    <span class="shortcut"><kbd>Enter</kbd> view</span>
    <span class="shortcut"><kbd>e</kbd> edit</span>
    <span class="shortcut"><kbd>a</kbd> add</span>
    <span class="shortcut"><kbd>d</kbd> delete</span>
    <span class="shortcut"><kbd>h</kbd><kbd>l</kbd> month</span>
    <span class="shortcut"><kbd>t</kbd> this month</span>
    <span class="shortcut"><kbd>⌘↑</kbd><kbd>⌘↓</kbd> reorder</span>
  </div>

  <Modal
    open={showTransactions && !!drillDownCategory}
    title="{drillDownCategory?.category ?? ''} — {formatMonth(selectedMonth)}"
    onclose={closeDrillDown}
    width="500px"
  >
    {#if drillDownLoading}
      <div class="modal-loading">Loading...</div>
    {:else if drillDownTransactions.length === 0}
      <div class="modal-empty">No transactions</div>
    {:else}
      <div class="txn-list">
        {#each drillDownTransactions as txn}
          <div class="txn-row">
            <span class="txn-date">{txn.transaction_date}</span>
            <span class="txn-desc">{txn.description}</span>
            <span class="txn-amount" class:negative={txn.amount < 0}>${formatAmount(txn.amount)}</span>
          </div>
        {/each}
      </div>
      <div class="modal-footer">
        <span>{drillDownTransactions.length} transactions</span>
        <span class="mono">Total: {formatCurrency(drillDownTransactions.reduce((s, t) => s + Math.abs(t.amount), 0))}</span>
      </div>
    {/if}

    {#snippet actions()}
      <button class="btn danger" onclick={handleModalDelete}>Delete</button>
      <button class="btn secondary" onclick={handleModalEdit}>Edit</button>
    {/snippet}
  </Modal>

  <Modal
    open={isEditing}
    title="{editingCategory ? 'Edit' : 'Add'} Category"
    onclose={cancelEdit}
    width="500px"
  >
    <div class="form">
      <label>Type<select bind:value={editorForm.type}><option value="income">Income</option><option value="expense">Expense</option></select></label>
      <label>Name<input type="text" bind:value={editorForm.category} placeholder="e.g., Groceries" /></label>
      <label>Expected<input type="number" bind:value={editorForm.expected} min="0" step="100" /></label>
      <label>Tags (comma-separated)<input type="text" bind:value={editorForm.tags} placeholder="e.g., groceries, food" /></label>
      <label class="checkbox"><input type="checkbox" bind:checked={editorForm.require_all} /> Require ALL tags</label>
    </div>

    {#snippet actions()}
      <button class="btn secondary" onclick={cancelEdit}>Cancel</button>
      <button class="btn primary" onclick={saveCategory}>Save</button>
    {/snippet}
  </Modal>

  <!-- Transfer Modal (supports multiple transfers from one source) -->
  <Modal
    open={showTransferModal}
    title="Transfer: {formatMonth(transferStorageMonth)} → {formatMonth(getNextMonth(transferStorageMonth))}"
    onclose={closeTransferModal}
    width="450px"
  >
    <div class="transfer-modal-content">
      <div class="transfer-header">
        <span class="transfer-source">From: {transferSourceCategory}</span>
        {#if transferSourceVariance !== 0}
          <span class="transfer-variance" class:positive={transferSourceVariance >= 0} class:negative={transferSourceVariance < 0}>
            {transferSourceVariance >= 0 ? 'Surplus' : 'Deficit'}: {formatCurrency(Math.abs(transferSourceVariance))}
          </span>
        {/if}
      </div>

      <div class="transfer-rows">
        {#each transferRows as row, i (row.id)}
          <div class="transfer-row">
            <label class="transfer-to-label">
              To
              <select bind:value={row.toCategory}>
                {#each availableTransferCategories as cat}
                  <option value={cat}>{cat}</option>
                {/each}
              </select>
            </label>
            <label class="transfer-amount-label">
              Amount
              <input
                type="number"
                bind:value={row.amount}
                step="1"
              />
            </label>
            {#if transferRows.length > 1}
              <button class="transfer-row-delete" onclick={() => removeTransferRow(row.id)} title="Remove">×</button>
            {/if}
          </div>
        {/each}
      </div>

      <button class="add-transfer-btn" onclick={addTransferRow}>+ Add another transfer</button>

      {#if transferSourceVariance !== 0}
        <div class="transfer-summary">
          <div class="transfer-summary-row">
            <span>Allocated:</span>
            <span class="mono">{formatCurrency(totalAllocated)} / {formatCurrency(transferSourceVariance)}</span>
          </div>
          <div class="transfer-summary-row">
            <span>Remaining:</span>
            <span class="mono" class:positive={remainingToAllocate >= 0} class:negative={remainingToAllocate < 0}>
              {formatCurrency(remainingToAllocate)}
            </span>
          </div>
        </div>
      {/if}
    </div>

    {#snippet actions()}
      {#if isEditingTransfers}
        <button class="btn danger" onclick={removeAllTransfers}>Remove All</button>
      {/if}
      <div style="flex: 1;"></div>
      <button class="btn secondary" onclick={closeTransferModal}>Cancel</button>
      <button class="btn primary" onclick={saveTransfers}>Save</button>
    {/snippet}
  </Modal>

  <!-- Reset Budget Modal -->
  <Modal
    open={showResetModal}
    title="Reset Budget — {formatMonth(selectedMonth)}"
    onclose={closeResetModal}
    width="400px"
  >
    <div class="reset-modal-content">
      {#if monthsWithData.filter(m => m !== selectedMonth).length > 0}
        <div class="reset-form-group">
          <label class="reset-label">Copy from another month</label>
          <div class="reset-row">
            <select bind:value={resetSourceMonth}>
              {#each monthsWithData.filter(m => m !== selectedMonth) as month}
                <option value={month}>{formatMonth(month)}</option>
              {/each}
            </select>
            <button class="reset-copy-btn" onclick={resetFromMonth} disabled={!resetSourceMonth}>Copy</button>
          </div>
        </div>

        <div class="reset-divider">
          <span>or</span>
        </div>
      {/if}

      <div class="reset-form-group">
        <label class="reset-label">Delete budget</label>
        <p class="reset-hint">Remove all categories and transfers for this month.</p>
        <button class="reset-delete-btn" onclick={deleteBudget}>Delete Budget</button>
      </div>
    </div>

    {#snippet actions()}
      <button class="btn secondary" onclick={closeResetModal}>Cancel</button>
    {/snippet}
  </Modal>
</div>

<style>
  .budget-view {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
    outline: none;
  }

  .header {
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
    background: var(--bg-secondary);
  }

  .title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-md);
  }

  .title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .month-nav {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .nav-btn {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    color: var(--text-primary);
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
  }

  .nav-btn:hover:not(:disabled) { background: var(--bg-primary); }
  .nav-btn:disabled { opacity: 0.3; cursor: default; }

  .this-month-btn {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    color: var(--text-secondary);
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    font-weight: 500;
    margin-left: var(--spacing-sm);
    transition: all 0.15s ease;
  }

  .this-month-btn:hover:not(:disabled) {
    background: var(--bg-primary);
    color: var(--text-primary);
    border-color: var(--accent-primary);
  }

  .this-month-btn:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .reset-btn {
    background: transparent;
    border: 1px solid var(--border-primary);
    color: var(--text-muted);
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    font-weight: 500;
    margin-left: var(--spacing-sm);
    transition: all 0.15s ease;
  }

  .reset-btn:hover:not(:disabled) {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--accent-danger);
  }

  .reset-btn:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .current-month {
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    min-width: 80px;
    text-align: center;
  }

  .error-bar {
    padding: var(--spacing-sm) var(--spacing-lg);
    background: var(--accent-danger);
    color: white;
    font-size: 12px;
  }

  .main-content {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .list-container {
    flex: 1;
    overflow-y: auto;
    font-family: var(--font-mono);
    font-size: 13px;
  }

  .empty-state {
    padding: var(--spacing-xl);
    text-align: center;
    color: var(--text-muted);
  }

  .empty-state kbd {
    padding: 2px 6px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 3px;
    font-family: var(--font-mono);
  }

  /* Copy from previous month prompt */
  .copy-from-previous {
    padding: var(--spacing-xl);
    text-align: center;
  }

  .copy-prompt p {
    margin: 0 0 var(--spacing-sm) 0;
    color: var(--text-primary);
  }

  .copy-prompt .copy-hint {
    color: var(--text-muted);
    font-size: 13px;
    margin-bottom: var(--spacing-lg);
  }

  .copy-actions {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    align-items: center;
  }

  .copy-select-row {
    display: flex;
    gap: var(--spacing-sm);
    align-items: center;
  }

  .copy-month-select {
    padding: 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 28px;
    cursor: pointer;
  }

  .copy-month-select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .copy-month-select option {
    background: var(--bg-secondary);
    color: var(--text-primary);
    padding: 8px;
  }

  .copy-actions .btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
  }

  .copy-actions .btn.primary {
    background: var(--accent-primary);
    color: white;
    border: none;
  }

  .copy-actions .btn.primary:hover {
    opacity: 0.9;
  }

  .copy-actions .btn.secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
  }

  .copy-actions .btn.secondary:hover {
    background: var(--bg-primary);
  }

  /* Section divider */
  .section-divider {
    height: 12px;
    background: var(--bg-primary);
    border-top: 1px solid var(--border-primary);
    border-bottom: 1px solid var(--border-primary);
  }

  /* Income header - green accent */
  .section-header.income-header {
    border-left: 3px solid var(--accent-success, #22c55e);
    padding-left: calc(var(--spacing-lg) - 3px);
  }

  .section-header.income-header .section-title {
    color: var(--accent-success, #22c55e);
  }

  /* Budget header - blue accent */
  .section-header.budget-header {
    border-left: 3px solid var(--accent-primary, #3b82f6);
    padding-left: calc(var(--spacing-lg) - 3px);
  }

  .section-header.budget-header .section-title {
    color: var(--accent-primary, #3b82f6);
  }


  /* Remaining Row */
  .remaining-row {
    display: flex;
    align-items: center;
    padding: 10px var(--spacing-lg);
    margin-top: var(--spacing-sm);
    background: var(--bg-secondary);
    border-top: 2px solid var(--border-primary);
    gap: var(--spacing-md);
  }

  .remaining-label {
    font-weight: 700;
    color: var(--text-primary);
  }

  .section-header {
    display: flex;
    align-items: center;
    padding: 8px var(--spacing-lg);
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-primary);
    gap: var(--spacing-md);
  }

  .section-title {
    font-weight: 700;
    color: var(--text-primary);
  }

  .add-row {
    display: block;
    width: 100%;
    padding: 6px var(--spacing-lg);
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--border-primary);
    color: var(--text-muted);
    font-size: 12px;
    font-family: var(--font-mono);
    text-align: left;
    cursor: pointer;
  }

  .add-row:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
  }

  .row {
    display: flex;
    align-items: center;
    padding: 8px var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
    gap: var(--spacing-md);
    cursor: pointer;
  }

  .row:hover { background: var(--bg-secondary); }

  .row.cursor {
    background: var(--bg-tertiary);
    border-left: 3px solid var(--text-muted);
    padding-left: calc(var(--spacing-lg) - 3px);
  }

  .row-details-placeholder {
    width: 24px;
    flex-shrink: 0;
  }

  .transfer-btn-placeholder {
    width: 24px;
    margin-right: 4px;
    flex-shrink: 0;
  }


  .row-name {
    width: 220px;
    flex-shrink: 0;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .row-bar {
    flex: 1;
    min-width: 100px;
  }

  .bar-bg {
    height: 6px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.2s;
  }

  .row-actual {
    width: 80px;
    text-align: right;
    color: var(--text-primary);
    font-weight: 600;
  }

  .row-expected {
    width: 80px;
    text-align: right;
    color: var(--text-muted);
  }

  .row-percent {
    width: 50px;
    text-align: right;
    font-weight: 600;
  }

  .sidebar {
    width: 200px;
    flex-shrink: 0;
    border-left: 1px solid var(--border-primary);
    background: var(--bg-secondary);
    padding: var(--spacing-md);
    overflow-y: auto;
  }

  .sidebar-section { margin-bottom: var(--spacing-lg); }

  .sidebar-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--spacing-sm);
  }

  .sidebar-empty {
    color: var(--text-muted);
    font-size: 12px;
    font-style: italic;
  }

  .trend-empty {
    color: var(--text-muted);
    font-size: 11px;
    font-style: italic;
  }

  .trend-chart {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .trend-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
  }

  .trend-month {
    width: 24px;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .trend-bar-container {
    flex: 1;
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: 2px;
    overflow: hidden;
  }

  .trend-bar {
    height: 100%;
    background: var(--accent-primary);
    border-radius: 2px;
    transition: width 0.2s;
  }

  .trend-amount {
    width: 55px;
    text-align: right;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    flex-shrink: 0;
  }

  .trend-avg {
    margin-top: 6px;
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .detail-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .detail-type {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: capitalize;
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .tag {
    padding: 2px 6px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
  }

  .tag-mode {
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 4px;
    font-style: italic;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .mono { font-family: var(--font-mono); }
  .positive { color: var(--accent-success, #22c55e) !important; }
  .negative { color: var(--accent-danger, #ef4444) !important; }

  /* Modal content styles */
  .modal-loading, .modal-empty {
    padding: var(--spacing-xl);
    text-align: center;
    color: var(--text-muted);
  }

  .txn-list {
    flex: 1;
    overflow-y: auto;
    font-family: var(--font-mono);
    font-size: 12px;
  }

  .txn-row {
    display: flex;
    gap: var(--spacing-md);
    padding: 6px var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
  }

  .txn-date {
    width: 80px;
    color: var(--text-muted);
  }

  .txn-desc {
    flex: 1;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .txn-amount {
    width: 70px;
    text-align: right;
    color: var(--text-primary);
  }

  .txn-amount.negative { color: var(--accent-danger, #ef4444); }

  .modal-footer {
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-lg);
    border-top: 1px solid var(--border-primary);
    font-size: 12px;
    color: var(--text-muted);
  }

  .form {
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .form label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .form label.checkbox {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }

  .form input, .form select {
    padding: 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
  }

  .form input:focus, .form select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  /* Custom select styling */
  .form select {
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 28px;
    cursor: pointer;
  }

  .form select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .form select option {
    background: var(--bg-secondary);
    color: var(--text-primary);
    padding: 8px;
  }

  /* Shortcuts footer */
  .shortcuts-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px var(--spacing-lg);
    gap: var(--spacing-lg);
    flex-wrap: wrap;
    border-top: 1px solid var(--border-primary);
    background: var(--bg-secondary);
  }

  .shortcut {
    font-size: 11px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .shortcut kbd {
    display: inline-block;
    padding: 2px 5px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-secondary);
    margin-right: 2px;
  }

  /* Transfer badge (row inline) */
  .transfer-badge {
    display: inline-block;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
  }

  .transfer-badge.incoming {
    margin-right: 6px;
  }

  .transfer-badge.outgoing {
    margin-left: 6px;
    opacity: 0.8;
  }

  .transfer-badge.positive {
    background: rgba(34, 197, 94, 0.15);
    color: var(--accent-success, #22c55e);
  }

  .transfer-badge.negative {
    background: rgba(239, 68, 68, 0.15);
    color: var(--accent-danger, #ef4444);
  }

  /* Make transfer badge look like a button when clickable */
  button.transfer-badge {
    cursor: pointer;
    border: none;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }

  button.transfer-badge:hover {
    transform: scale(1.05);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }

  /* Transfer arrow button */
  .transfer-btn {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-muted);
    font-size: 14px;
    cursor: pointer;
    flex-shrink: 0;
    margin-right: 4px;
  }

  .transfer-btn:hover {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: white;
  }

  .transfer-btn.has-outgoing {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: white;
  }

  .transfer-btn.has-outgoing:hover {
    filter: brightness(1.1);
  }

  /* Transfer modal */
  .transfer-modal-content {
    padding: var(--spacing-md) var(--spacing-lg);
  }

  .transfer-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: var(--spacing-lg);
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
  }

  .transfer-source {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .transfer-variance {
    font-size: 12px;
    font-family: var(--font-mono);
  }

  .transfer-rows {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .transfer-row {
    display: flex;
    gap: var(--spacing-sm);
    align-items: flex-end;
  }

  .transfer-to-label {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .transfer-to-label select {
    padding: 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 28px;
    cursor: pointer;
  }

  .transfer-to-label select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .transfer-amount-label {
    width: 100px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .transfer-amount-label input {
    padding: 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
    font-family: var(--font-mono);
  }

  .transfer-amount-label input:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .transfer-row-delete {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-muted);
    font-size: 18px;
    cursor: pointer;
  }

  .transfer-row-delete:hover {
    background: var(--accent-danger);
    border-color: var(--accent-danger);
    color: white;
  }

  .add-transfer-btn {
    width: 100%;
    padding: 8px;
    background: transparent;
    border: 1px dashed var(--border-primary);
    border-radius: 4px;
    color: var(--text-muted);
    font-size: 12px;
    cursor: pointer;
    margin-bottom: var(--spacing-md);
  }

  .add-transfer-btn:hover {
    background: var(--bg-tertiary);
    border-color: var(--accent-primary);
    color: var(--text-primary);
  }

  .transfer-summary {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: 4px;
    font-size: 12px;
  }

  .transfer-summary-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
    color: var(--text-secondary);
  }

  .transfer-summary-row:last-child {
    margin-bottom: 0;
  }

  /* Sidebar transfer details */
  .transfer-group {
    margin-bottom: var(--spacing-md);
    padding: var(--spacing-sm);
    border-radius: 4px;
  }

  .transfer-group.incoming {
    background: rgba(59, 130, 246, 0.1);
    border-left: 2px solid var(--accent-primary);
  }

  .transfer-group.outgoing {
    background: rgba(107, 114, 128, 0.1);
    border-left: 2px solid var(--text-muted);
  }

  .transfer-group-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .transfer-detail {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    padding: 2px 0;
  }

  .transfer-from, .transfer-to {
    color: var(--text-secondary);
  }

  .transfer-amount {
    font-family: var(--font-mono);
    font-weight: 600;
  }

  .transfer-total {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    padding-top: 4px;
    margin-top: 4px;
    border-top: 1px solid var(--border-primary);
    color: var(--text-secondary);
  }

  /* Reset modal styles */
  .reset-modal-content {
    padding: var(--spacing-lg);
  }

  .reset-form-group {
    margin-bottom: var(--spacing-md);
  }

  .reset-label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .reset-row {
    display: flex;
    gap: var(--spacing-sm);
    align-items: center;
  }

  .reset-modal-content select {
    flex: 1;
    padding: 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 28px;
    cursor: pointer;
  }

  .reset-modal-content select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .reset-modal-content select option {
    background: var(--bg-secondary);
    color: var(--text-primary);
    padding: 8px;
  }

  .reset-copy-btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: none;
    background: var(--accent-primary);
    color: white;
    transition: opacity 0.15s;
  }

  .reset-copy-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .reset-copy-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .reset-divider {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin: var(--spacing-lg) 0;
    color: var(--text-muted);
    font-size: 12px;
  }

  .reset-divider::before,
  .reset-divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--border-primary);
  }

  .reset-hint {
    margin: 0 0 var(--spacing-sm) 0;
    font-size: 12px;
    color: var(--text-muted);
  }

  .reset-delete-btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: none;
    background: var(--accent-danger);
    color: white;
    transition: opacity 0.15s;
  }

  .reset-delete-btn:hover {
    opacity: 0.9;
  }
</style>
