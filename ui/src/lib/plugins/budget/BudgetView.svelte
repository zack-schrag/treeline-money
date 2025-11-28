<script lang="ts">
  import { onMount } from "svelte";
  import { invoke } from "@tauri-apps/api/core";
  import { executeQuery } from "../../sdk";
  import type { BudgetCategory, BudgetActual, BudgetType, AmountSign, BudgetConfig, MonthSummary, Transaction } from "./types";

  const PLUGIN_ID = "budget";
  const CONFIG_FILE = "budget_config.json";

  // State
  let categories = $state<BudgetCategory[]>([]);
  let actuals = $state<BudgetActual[]>([]);
  let compareActuals = $state<BudgetActual[]>([]);
  let isLoading = $state(true);
  let error = $state<string | null>(null);

  // Month selection
  let availableMonths = $state<string[]>([]);
  let selectedMonth = $state<string>("");
  let compareMonth = $state<string>("");
  let isCompareMode = $state(false);

  // Account filtering
  let allAccounts = $state<string[]>([]);
  let selectedAccounts = $state<string[]>([]);
  let showAccountFilter = $state(false);

  // Trend data for hero chart
  let monthTrends = $state<MonthSummary[]>([]);

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

  // Transaction drill-down
  let showTransactions = $state(false);
  let drillDownCategory = $state<BudgetActual | null>(null);
  let drillDownTransactions = $state<Transaction[]>([]);
  let drillDownLoading = $state(false);

  // All known tags for autocomplete
  let allTags = $state<string[]>([]);

  // Computed summaries
  let incomeSummary = $derived({
    expected: actuals.filter(a => a.type === "income").reduce((sum, a) => sum + a.expected, 0),
    actual: actuals.filter(a => a.type === "income").reduce((sum, a) => sum + a.actual, 0),
  });

  let expenseSummary = $derived({
    expected: actuals.filter(a => a.type === "expense").reduce((sum, a) => sum + a.expected, 0),
    actual: actuals.filter(a => a.type === "expense").reduce((sum, a) => sum + a.actual, 0),
  });

  let savingsSummary = $derived({
    expected: actuals.filter(a => a.type === "savings").reduce((sum, a) => sum + a.expected, 0),
    actual: actuals.filter(a => a.type === "savings").reduce((sum, a) => sum + a.actual, 0),
  });

  let netAmount = $derived(incomeSummary.actual - expenseSummary.actual - savingsSummary.actual);

  // Compare summaries
  let compareIncomeSummary = $derived({
    expected: compareActuals.filter(a => a.type === "income").reduce((sum, a) => sum + a.expected, 0),
    actual: compareActuals.filter(a => a.type === "income").reduce((sum, a) => sum + a.actual, 0),
  });

  let compareExpenseSummary = $derived({
    expected: compareActuals.filter(a => a.type === "expense").reduce((sum, a) => sum + a.expected, 0),
    actual: compareActuals.filter(a => a.type === "expense").reduce((sum, a) => sum + a.actual, 0),
  });

  let compareSavingsSummary = $derived({
    expected: compareActuals.filter(a => a.type === "savings").reduce((sum, a) => sum + a.expected, 0),
    actual: compareActuals.filter(a => a.type === "savings").reduce((sum, a) => sum + a.actual, 0),
  });

  let compareNetAmount = $derived(compareIncomeSummary.actual - compareExpenseSummary.actual - compareSavingsSummary.actual);

  // Group actuals by type
  let incomeActuals = $derived(actuals.filter(a => a.type === "income"));
  let expenseActuals = $derived(actuals.filter(a => a.type === "expense"));
  let savingsActuals = $derived(actuals.filter(a => a.type === "savings"));

  // Chart dimensions
  const CHART_HEIGHT = 160;
  const CHART_PADDING = 40;

  // Compute chart data
  let chartData = $derived.by(() => {
    if (monthTrends.length === 0) return null;

    const maxValue = Math.max(
      ...monthTrends.flatMap(m => [m.income, m.expenses, m.savings])
    ) * 1.1;

    const barWidth = Math.min(60, (800 - CHART_PADDING * 2) / monthTrends.length / 3 - 4);
    const groupWidth = barWidth * 3 + 12;

    return { maxValue, barWidth, groupWidth };
  });

  // Convert BudgetConfig JSON to flat category array
  function configToCategories(config: BudgetConfig): BudgetCategory[] {
    const result: BudgetCategory[] = [];

    for (const [category, data] of Object.entries(config.income || {})) {
      result.push({
        id: `income-${category}`,
        type: "income",
        category,
        expected: data.expected,
        tags: data.tags,
        require_all: data.require_all || false,
        amount_sign: data.amount_sign || null,
      });
    }

    for (const [category, data] of Object.entries(config.expenses || {})) {
      result.push({
        id: `expense-${category}`,
        type: "expense",
        category,
        expected: data.expected,
        tags: data.tags,
        require_all: data.require_all || false,
        amount_sign: data.amount_sign || null,
      });
    }

    for (const [category, data] of Object.entries(config.savings || {})) {
      result.push({
        id: `savings-${category}`,
        type: "savings",
        category,
        expected: data.expected,
        tags: data.tags,
        require_all: data.require_all || false,
        amount_sign: data.amount_sign || null,
      });
    }

    return result;
  }

  // Convert flat category array back to BudgetConfig JSON
  function categoriesToConfig(cats: BudgetCategory[]): BudgetConfig {
    const config: BudgetConfig = {
      income: {},
      expenses: {},
      savings: {},
      selectedAccounts: selectedAccounts.length > 0 ? selectedAccounts : undefined,
    };

    for (const cat of cats) {
      const data: { expected: number; tags: string[]; require_all?: boolean; amount_sign?: AmountSign } = {
        expected: cat.expected,
        tags: cat.tags,
      };
      if (cat.require_all) data.require_all = true;
      if (cat.amount_sign) data.amount_sign = cat.amount_sign;

      if (cat.type === "income") {
        config.income[cat.category] = data;
      } else if (cat.type === "expense") {
        config.expenses[cat.category] = data;
      } else if (cat.type === "savings") {
        config.savings[cat.category] = data;
      }
    }

    return config;
  }

  async function loadConfig(): Promise<BudgetConfig> {
    try {
      const content = await invoke<string>("read_plugin_config", {
        pluginId: PLUGIN_ID,
        filename: CONFIG_FILE,
      });

      if (content === "null" || !content) {
        return { income: {}, expenses: {}, savings: {} };
      }

      return JSON.parse(content);
    } catch (e) {
      console.error("Failed to load config:", e);
      return { income: {}, expenses: {}, savings: {} };
    }
  }

  async function saveConfig(config: BudgetConfig): Promise<void> {
    const content = JSON.stringify(config, null, 2);
    await invoke("write_plugin_config", {
      pluginId: PLUGIN_ID,
      filename: CONFIG_FILE,
      content,
    });
  }

  async function loadAvailableMonths() {
    const result = await executeQuery(`
      SELECT DISTINCT strftime('%Y-%m', transaction_date) as month
      FROM transactions
      ORDER BY month DESC
    `);
    availableMonths = result.rows.map(r => r[0] as string);
    if (availableMonths.length > 0 && !selectedMonth) {
      selectedMonth = availableMonths[0];
    }
    if (availableMonths.length > 1 && !compareMonth) {
      compareMonth = availableMonths[1];
    }
  }

  async function loadAllAccounts() {
    const result = await executeQuery(`
      SELECT DISTINCT account_name
      FROM transactions
      WHERE account_name IS NOT NULL AND account_name != ''
      ORDER BY account_name
    `);
    allAccounts = result.rows.map(r => r[0] as string);
  }

  async function loadAllTags() {
    const result = await executeQuery(`
      SELECT DISTINCT unnest(tags) as tag
      FROM transactions
      WHERE tags != []
      ORDER BY tag
    `);
    allTags = result.rows.map(r => r[0] as string);
  }

  async function loadCategories() {
    const config = await loadConfig();
    categories = configToCategories(config);
    if (config.selectedAccounts && config.selectedAccounts.length > 0) {
      selectedAccounts = config.selectedAccounts;
    }
  }

  function buildAccountFilter(): string {
    if (selectedAccounts.length === 0) return "";
    const escaped = selectedAccounts.map(a => `'${a.replace(/'/g, "''")}'`);
    return `AND account_name IN (${escaped.join(", ")})`;
  }

  async function calculateActualsForMonth(month: string): Promise<BudgetActual[]> {
    if (!month || categories.length === 0) {
      return [];
    }

    const accountFilter = buildAccountFilter();
    const newActuals: BudgetActual[] = [];

    for (const cat of categories) {
      const defaultSign = cat.type === "income" ? "positive" : "negative";
      const effectiveSign = cat.amount_sign || defaultSign;

      let tagCondition: string;
      if (cat.require_all) {
        const tagChecks = cat.tags.map(t => `list_contains(tags, '${t.replace(/'/g, "''")}')`);
        tagCondition = tagChecks.join(" AND ");
      } else {
        const escapedTags = cat.tags.map(t => `'${t.replace(/'/g, "''")}'`);
        tagCondition = `list_has_any(tags, [${escapedTags.join(", ")}])`;
      }

      let amountCondition = "";
      if (effectiveSign === "positive") {
        amountCondition = "AND amount > 0";
      } else if (effectiveSign === "negative") {
        amountCondition = "AND amount < 0";
      }

      const query = `
        SELECT COALESCE(SUM(ABS(amount)), 0) as total
        FROM transactions
        WHERE strftime('%Y-%m', transaction_date) = '${month}'
          AND ${tagCondition}
          ${amountCondition}
          ${accountFilter}
      `;

      try {
        const result = await executeQuery(query);
        const actual = result.rows[0]?.[0] as number || 0;

        const variance = cat.type === "income"
          ? actual - cat.expected
          : cat.expected - actual;

        const percentUsed = cat.expected > 0
          ? Math.round((actual / cat.expected) * 100)
          : (actual > 0 ? 100 : 0);

        newActuals.push({
          id: cat.id,
          type: cat.type,
          category: cat.category,
          expected: cat.expected,
          actual,
          variance,
          percentUsed,
        });
      } catch (e) {
        console.error(`Failed to calculate actual for ${cat.category}:`, e);
      }
    }

    return newActuals;
  }

  async function calculateActuals() {
    actuals = await calculateActualsForMonth(selectedMonth);
    if (isCompareMode && compareMonth) {
      compareActuals = await calculateActualsForMonth(compareMonth);
    }
  }

  async function loadMonthTrends() {
    if (categories.length === 0) {
      monthTrends = [];
      return;
    }

    const accountFilter = buildAccountFilter();
    const trends: MonthSummary[] = [];

    // Get last 6 months
    const months = availableMonths.slice(0, 6).reverse();

    for (const month of months) {
      let income = 0;
      let expenses = 0;
      let savings = 0;

      for (const cat of categories) {
        const defaultSign = cat.type === "income" ? "positive" : "negative";
        const effectiveSign = cat.amount_sign || defaultSign;

        let tagCondition: string;
        if (cat.require_all) {
          const tagChecks = cat.tags.map(t => `list_contains(tags, '${t.replace(/'/g, "''")}')`);
          tagCondition = tagChecks.join(" AND ");
        } else {
          const escapedTags = cat.tags.map(t => `'${t.replace(/'/g, "''")}'`);
          tagCondition = `list_has_any(tags, [${escapedTags.join(", ")}])`;
        }

        let amountCondition = "";
        if (effectiveSign === "positive") {
          amountCondition = "AND amount > 0";
        } else if (effectiveSign === "negative") {
          amountCondition = "AND amount < 0";
        }

        const query = `
          SELECT COALESCE(SUM(ABS(amount)), 0) as total
          FROM transactions
          WHERE strftime('%Y-%m', transaction_date) = '${month}'
            AND ${tagCondition}
            ${amountCondition}
            ${accountFilter}
        `;

        try {
          const result = await executeQuery(query);
          const actual = result.rows[0]?.[0] as number || 0;

          if (cat.type === "income") income += actual;
          else if (cat.type === "expense") expenses += actual;
          else if (cat.type === "savings") savings += actual;
        } catch (e) {
          console.error(`Failed to load trend for ${cat.category} in ${month}:`, e);
        }
      }

      trends.push({
        month,
        income,
        expenses,
        savings,
        net: income - expenses - savings,
      });
    }

    monthTrends = trends;
  }

  async function loadAll() {
    isLoading = true;
    error = null;

    try {
      await Promise.all([
        loadAvailableMonths(),
        loadCategories(),
        loadAllTags(),
        loadAllAccounts(),
      ]);
      await calculateActuals();
      await loadMonthTrends();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load budget data";
      console.error("Failed to load budget:", e);
    } finally {
      isLoading = false;
    }
  }

  async function loadTransactionsForCategory(cat: BudgetActual) {
    drillDownCategory = cat;
    drillDownLoading = true;
    showTransactions = true;

    const category = categories.find(c => c.id === cat.id);
    if (!category) {
      drillDownLoading = false;
      return;
    }

    const accountFilter = buildAccountFilter();
    const defaultSign = category.type === "income" ? "positive" : "negative";
    const effectiveSign = category.amount_sign || defaultSign;

    let tagCondition: string;
    if (category.require_all) {
      const tagChecks = category.tags.map(t => `list_contains(tags, '${t.replace(/'/g, "''")}')`);
      tagCondition = tagChecks.join(" AND ");
    } else {
      const escapedTags = category.tags.map(t => `'${t.replace(/'/g, "''")}'`);
      tagCondition = `list_has_any(tags, [${escapedTags.join(", ")}])`;
    }

    let amountCondition = "";
    if (effectiveSign === "positive") {
      amountCondition = "AND amount > 0";
    } else if (effectiveSign === "negative") {
      amountCondition = "AND amount < 0";
    }

    const query = `
      SELECT transaction_id, transaction_date, description, amount, tags, account_name
      FROM transactions
      WHERE strftime('%Y-%m', transaction_date) = '${selectedMonth}'
        AND ${tagCondition}
        ${amountCondition}
        ${accountFilter}
      ORDER BY transaction_date DESC
    `;

    try {
      const result = await executeQuery(query);
      drillDownTransactions = result.rows.map(row => ({
        transaction_id: row[0] as string,
        transaction_date: row[1] as string,
        description: row[2] as string,
        amount: row[3] as number,
        tags: (row[4] as string[]) || [],
        account_name: row[5] as string,
      }));
    } catch (e) {
      console.error("Failed to load transactions:", e);
      drillDownTransactions = [];
    } finally {
      drillDownLoading = false;
    }
  }

  function closeDrillDown() {
    showTransactions = false;
    drillDownCategory = null;
    drillDownTransactions = [];
  }

  function startAddCategory(type: BudgetType) {
    editingCategory = null;
    editorForm = {
      type,
      category: "",
      expected: 0,
      tags: "",
      require_all: false,
      amount_sign: null,
    };
    isEditing = true;
  }

  function startEditCategory(cat: BudgetCategory) {
    editingCategory = cat;
    editorForm = {
      type: cat.type,
      category: cat.category,
      expected: cat.expected,
      tags: cat.tags.join(", "),
      require_all: cat.require_all,
      amount_sign: cat.amount_sign,
    };
    isEditing = true;
  }

  function cancelEdit() {
    isEditing = false;
    editingCategory = null;
  }

  async function saveCategory() {
    const tags = editorForm.tags
      .split(",")
      .map(t => t.trim())
      .filter(t => t);

    if (!editorForm.category.trim() || tags.length === 0) {
      return;
    }

    try {
      const newCategory: BudgetCategory = {
        id: `${editorForm.type}-${editorForm.category}`,
        type: editorForm.type,
        category: editorForm.category.trim(),
        expected: editorForm.expected,
        tags,
        require_all: editorForm.require_all,
        amount_sign: editorForm.amount_sign,
      };

      let updatedCategories = categories.filter(c =>
        editingCategory ? c.id !== editingCategory.id : true
      );

      updatedCategories.push(newCategory);

      const config = categoriesToConfig(updatedCategories);
      await saveConfig(config);

      cancelEdit();
      await loadCategories();
      await calculateActuals();
      await loadMonthTrends();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to save category";
      console.error("Failed to save category:", e);
    }
  }

  async function deleteCategory(cat: BudgetCategory) {
    if (!confirm(`Delete "${cat.category}"?`)) return;

    try {
      const updatedCategories = categories.filter(c => c.id !== cat.id);
      const config = categoriesToConfig(updatedCategories);
      await saveConfig(config);

      await loadCategories();
      await calculateActuals();
      await loadMonthTrends();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to delete category";
      console.error("Failed to delete category:", e);
    }
  }

  async function toggleAccount(account: string) {
    if (selectedAccounts.includes(account)) {
      selectedAccounts = selectedAccounts.filter(a => a !== account);
    } else {
      selectedAccounts = [...selectedAccounts, account];
    }

    // Save to config
    const config = categoriesToConfig(categories);
    await saveConfig(config);

    // Recalculate
    await calculateActuals();
    await loadMonthTrends();
  }

  async function selectAllAccounts() {
    selectedAccounts = [];
    const config = categoriesToConfig(categories);
    await saveConfig(config);
    await calculateActuals();
    await loadMonthTrends();
  }

  function formatCurrency(amount: number): string {
    return amount.toLocaleString('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    });
  }

  function formatCurrencyShort(amount: number): string {
    if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}k`;
    }
    return `$${amount.toFixed(0)}`;
  }

  function getProgressColor(actual: BudgetActual): string {
    if (actual.type === "income") {
      return actual.percentUsed >= 100 ? "var(--accent-success, #22c55e)" : "var(--accent-primary)";
    } else {
      if (actual.percentUsed > 100) return "var(--accent-danger, #ef4444)";
      if (actual.percentUsed > 90) return "var(--accent-warning, #f59e0b)";
      return "var(--accent-success, #22c55e)";
    }
  }

  function getBarHeight(value: number, maxValue: number): number {
    if (maxValue === 0) return 0;
    return (value / maxValue) * (CHART_HEIGHT - 30);
  }

  // Recalculate when month changes
  $effect(() => {
    if (selectedMonth && categories.length > 0) {
      calculateActuals();
    }
  });

  // Recalculate compare when compare month changes
  $effect(() => {
    if (isCompareMode && compareMonth && categories.length > 0) {
      calculateActualsForMonth(compareMonth).then(result => {
        compareActuals = result;
      });
    }
  });

  onMount(() => {
    loadAll();
  });
</script>

<div class="budget-view">
  <!-- Header -->
  <div class="header">
    <div class="title-row">
      <h1 class="title">Budget</h1>
      <div class="header-controls">
        {#if availableMonths.length > 0}
          <select class="month-selector" bind:value={selectedMonth}>
            {#each availableMonths as month}
              <option value={month}>{month}</option>
            {/each}
          </select>

          <label class="compare-toggle">
            <input type="checkbox" bind:checked={isCompareMode} />
            Compare
          </label>

          {#if isCompareMode}
            <span class="compare-vs">vs</span>
            <select class="month-selector" bind:value={compareMonth}>
              {#each availableMonths.filter(m => m !== selectedMonth) as month}
                <option value={month}>{month}</option>
              {/each}
            </select>
          {/if}
        {/if}

        <button class="filter-btn" onclick={() => showAccountFilter = !showAccountFilter}>
          {selectedAccounts.length > 0 ? `${selectedAccounts.length} accounts` : "All accounts"}
        </button>
      </div>
    </div>

    <!-- Account Filter Dropdown -->
    {#if showAccountFilter}
      <div class="account-filter">
        <div class="filter-header">
          <span>Filter by Account</span>
          <button class="text-btn" onclick={selectAllAccounts}>
            {selectedAccounts.length > 0 ? "Clear filter" : "All selected"}
          </button>
        </div>
        <div class="account-list">
          {#each allAccounts as account}
            <label class="account-option">
              <input
                type="checkbox"
                checked={selectedAccounts.length === 0 || selectedAccounts.includes(account)}
                onchange={() => toggleAccount(account)}
              />
              {account}
            </label>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  {#if isLoading}
    <div class="loading">Loading budget...</div>
  {:else}
    <!-- Hero Chart -->
    {#if monthTrends.length > 0 && chartData}
      <div class="hero-chart">
        <div class="chart-title">Monthly Trends</div>
        <div class="chart-container">
          <svg class="chart" viewBox="0 0 800 {CHART_HEIGHT}" preserveAspectRatio="xMidYMid meet">
            <!-- Y-axis labels -->
            <text x="35" y="15" class="axis-label" text-anchor="end">{formatCurrencyShort(chartData.maxValue)}</text>
            <text x="35" y="{CHART_HEIGHT - 15}" class="axis-label" text-anchor="end">$0</text>

            <!-- Bars -->
            {#each monthTrends as trend, i}
              {@const x = CHART_PADDING + i * chartData.groupWidth + 20}
              {@const isSelected = trend.month === selectedMonth}

              <!-- Income bar -->
              <rect
                x={x}
                y={CHART_HEIGHT - 20 - getBarHeight(trend.income, chartData.maxValue)}
                width={chartData.barWidth}
                height={getBarHeight(trend.income, chartData.maxValue)}
                fill={isSelected ? "var(--accent-success, #22c55e)" : "rgba(34, 197, 94, 0.5)"}
                rx="2"
              />

              <!-- Expenses bar -->
              <rect
                x={x + chartData.barWidth + 4}
                y={CHART_HEIGHT - 20 - getBarHeight(trend.expenses, chartData.maxValue)}
                width={chartData.barWidth}
                height={getBarHeight(trend.expenses, chartData.maxValue)}
                fill={isSelected ? "var(--accent-danger, #ef4444)" : "rgba(239, 68, 68, 0.5)"}
                rx="2"
              />

              <!-- Savings bar -->
              <rect
                x={x + chartData.barWidth * 2 + 8}
                y={CHART_HEIGHT - 20 - getBarHeight(trend.savings, chartData.maxValue)}
                width={chartData.barWidth}
                height={getBarHeight(trend.savings, chartData.maxValue)}
                fill={isSelected ? "var(--accent-primary)" : "rgba(99, 102, 241, 0.5)"}
                rx="2"
              />

              <!-- Month label -->
              <text
                x={x + chartData.groupWidth / 2 - 10}
                y={CHART_HEIGHT - 3}
                class="month-label"
                class:selected={isSelected}
              >
                {trend.month.slice(5)}
              </text>
            {/each}
          </svg>

          <div class="chart-legend">
            <span class="legend-item income"><span class="dot"></span> Income</span>
            <span class="legend-item expense"><span class="dot"></span> Expenses</span>
            <span class="legend-item savings"><span class="dot"></span> Savings</span>
          </div>
        </div>
      </div>
    {/if}

    <!-- Summary Cards -->
    <div class="summary-cards" class:compare-mode={isCompareMode}>
      <div class="summary-card income">
        <div class="card-label">Income</div>
        <div class="card-actual">{formatCurrency(incomeSummary.actual)}</div>
        {#if isCompareMode}
          <div class="card-compare">vs {formatCurrency(compareIncomeSummary.actual)}</div>
        {:else}
          <div class="card-expected">of {formatCurrency(incomeSummary.expected)}</div>
        {/if}
      </div>
      <div class="summary-card expense">
        <div class="card-label">Expenses</div>
        <div class="card-actual">{formatCurrency(expenseSummary.actual)}</div>
        {#if isCompareMode}
          <div class="card-compare">vs {formatCurrency(compareExpenseSummary.actual)}</div>
        {:else}
          <div class="card-expected">of {formatCurrency(expenseSummary.expected)}</div>
        {/if}
      </div>
      <div class="summary-card savings">
        <div class="card-label">Savings</div>
        <div class="card-actual">{formatCurrency(savingsSummary.actual)}</div>
        {#if isCompareMode}
          <div class="card-compare">vs {formatCurrency(compareSavingsSummary.actual)}</div>
        {:else}
          <div class="card-expected">of {formatCurrency(savingsSummary.expected)}</div>
        {/if}
      </div>
      <div class="summary-card net" class:positive={netAmount >= 0} class:negative={netAmount < 0}>
        <div class="card-label">Net</div>
        <div class="card-actual">{formatCurrency(netAmount)}</div>
        {#if isCompareMode}
          <div class="card-compare">vs {formatCurrency(compareNetAmount)}</div>
        {:else}
          <div class="card-expected">{netAmount >= 0 ? "surplus" : "deficit"}</div>
        {/if}
      </div>
    </div>

    <!-- Budget Categories -->
    <div class="budget-sections">
      <!-- Income Section -->
      <div class="budget-section">
        <div class="section-header">
          <h2 class="section-title">Income</h2>
          <button class="add-btn" onclick={() => startAddCategory("income")}>+ Add</button>
        </div>
        {#if incomeActuals.length === 0}
          <div class="empty-section">No income categories. Click + Add to create one.</div>
        {:else}
          <div class="category-list">
            {#each incomeActuals as actual}
              {@const cat = categories.find(c => c.id === actual.id)}
              {@const compareActual = compareActuals.find(c => c.id === actual.id)}
              <div class="category-row" onclick={() => loadTransactionsForCategory(actual)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && loadTransactionsForCategory(actual)}>
                <div class="category-info">
                  <div class="category-name">{actual.category}</div>
                  <div class="category-tags">
                    {#if cat}
                      {#each cat.tags.slice(0, 3) as tag}
                        <span class="tag">{tag}</span>
                      {/each}
                      {#if cat.tags.length > 3}
                        <span class="tag-more">+{cat.tags.length - 3}</span>
                      {/if}
                    {/if}
                  </div>
                </div>
                <div class="category-progress">
                  <div class="progress-bar">
                    <div
                      class="progress-fill"
                      style="width: {Math.min(actual.percentUsed, 100)}%; background: {getProgressColor(actual)}"
                    ></div>
                  </div>
                  <div class="progress-text">
                    <span class="actual">{formatCurrency(actual.actual)}</span>
                    {#if isCompareMode && compareActual}
                      <span class="compare-value">vs {formatCurrency(compareActual.actual)}</span>
                    {:else}
                      <span class="expected">/ {formatCurrency(actual.expected)}</span>
                      <span class="percent">({actual.percentUsed}%)</span>
                    {/if}
                  </div>
                </div>
                <div class="category-actions">
                  {#if cat}
                    <button class="action-btn" onclick={(e) => { e.stopPropagation(); startEditCategory(cat); }}>Edit</button>
                    <button class="action-btn delete" onclick={(e) => { e.stopPropagation(); deleteCategory(cat); }}>Delete</button>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Expenses Section -->
      <div class="budget-section">
        <div class="section-header">
          <h2 class="section-title">Expenses</h2>
          <button class="add-btn" onclick={() => startAddCategory("expense")}>+ Add</button>
        </div>
        {#if expenseActuals.length === 0}
          <div class="empty-section">No expense categories. Click + Add to create one.</div>
        {:else}
          <div class="category-list">
            {#each expenseActuals as actual}
              {@const cat = categories.find(c => c.id === actual.id)}
              {@const compareActual = compareActuals.find(c => c.id === actual.id)}
              <div class="category-row" onclick={() => loadTransactionsForCategory(actual)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && loadTransactionsForCategory(actual)}>
                <div class="category-info">
                  <div class="category-name">{actual.category}</div>
                  <div class="category-tags">
                    {#if cat}
                      {#each cat.tags.slice(0, 3) as tag}
                        <span class="tag">{tag}</span>
                      {/each}
                      {#if cat.tags.length > 3}
                        <span class="tag-more">+{cat.tags.length - 3}</span>
                      {/if}
                    {/if}
                  </div>
                </div>
                <div class="category-progress">
                  <div class="progress-bar">
                    <div
                      class="progress-fill"
                      style="width: {Math.min(actual.percentUsed, 100)}%; background: {getProgressColor(actual)}"
                    ></div>
                  </div>
                  <div class="progress-text">
                    <span class="actual">{formatCurrency(actual.actual)}</span>
                    {#if isCompareMode && compareActual}
                      <span class="compare-value">vs {formatCurrency(compareActual.actual)}</span>
                    {:else}
                      <span class="expected">/ {formatCurrency(actual.expected)}</span>
                      <span class="percent" class:over={actual.percentUsed > 100}>({actual.percentUsed}%)</span>
                    {/if}
                  </div>
                </div>
                <div class="category-actions">
                  {#if cat}
                    <button class="action-btn" onclick={(e) => { e.stopPropagation(); startEditCategory(cat); }}>Edit</button>
                    <button class="action-btn delete" onclick={(e) => { e.stopPropagation(); deleteCategory(cat); }}>Delete</button>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Savings Section -->
      <div class="budget-section">
        <div class="section-header">
          <h2 class="section-title">Savings</h2>
          <button class="add-btn" onclick={() => startAddCategory("savings")}>+ Add</button>
        </div>
        {#if savingsActuals.length === 0}
          <div class="empty-section">No savings categories. Click + Add to create one.</div>
        {:else}
          <div class="category-list">
            {#each savingsActuals as actual}
              {@const cat = categories.find(c => c.id === actual.id)}
              {@const compareActual = compareActuals.find(c => c.id === actual.id)}
              <div class="category-row" onclick={() => loadTransactionsForCategory(actual)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && loadTransactionsForCategory(actual)}>
                <div class="category-info">
                  <div class="category-name">{actual.category}</div>
                  <div class="category-tags">
                    {#if cat}
                      {#each cat.tags.slice(0, 3) as tag}
                        <span class="tag">{tag}</span>
                      {/each}
                      {#if cat.tags.length > 3}
                        <span class="tag-more">+{cat.tags.length - 3}</span>
                      {/if}
                    {/if}
                  </div>
                </div>
                <div class="category-progress">
                  <div class="progress-bar">
                    <div
                      class="progress-fill"
                      style="width: {Math.min(actual.percentUsed, 100)}%; background: {getProgressColor(actual)}"
                    ></div>
                  </div>
                  <div class="progress-text">
                    <span class="actual">{formatCurrency(actual.actual)}</span>
                    {#if isCompareMode && compareActual}
                      <span class="compare-value">vs {formatCurrency(compareActual.actual)}</span>
                    {:else}
                      <span class="expected">/ {formatCurrency(actual.expected)}</span>
                      <span class="percent">({actual.percentUsed}%)</span>
                    {/if}
                  </div>
                </div>
                <div class="category-actions">
                  {#if cat}
                    <button class="action-btn" onclick={(e) => { e.stopPropagation(); startEditCategory(cat); }}>Edit</button>
                    <button class="action-btn delete" onclick={(e) => { e.stopPropagation(); deleteCategory(cat); }}>Delete</button>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Transaction Drill-down Modal -->
  {#if showTransactions}
    <div
      class="modal-overlay"
      onclick={closeDrillDown}
      onkeydown={(e) => e.key === "Escape" && closeDrillDown()}
      role="dialog"
      aria-modal="true"
      tabindex="-1"
    >
      <div class="modal transactions-modal" onclick={(e) => e.stopPropagation()} role="document">
        <div class="modal-header">
          <h3 class="modal-title">
            {drillDownCategory?.category} - {selectedMonth}
          </h3>
          <button class="close-btn" onclick={closeDrillDown}>×</button>
        </div>

        {#if drillDownLoading}
          <div class="modal-loading">Loading transactions...</div>
        {:else if drillDownTransactions.length === 0}
          <div class="modal-empty">No transactions found</div>
        {:else}
          <div class="transactions-list">
            {#each drillDownTransactions as txn}
              <div class="transaction-row">
                <div class="txn-date">{txn.transaction_date}</div>
                <div class="txn-desc">{txn.description}</div>
                <div class="txn-account">{txn.account_name}</div>
                <div class="txn-amount" class:negative={txn.amount < 0}>
                  {formatCurrency(Math.abs(txn.amount))}
                </div>
              </div>
            {/each}
          </div>
          <div class="modal-footer">
            <span class="txn-count">{drillDownTransactions.length} transactions</span>
            <span class="txn-total">
              Total: {formatCurrency(drillDownTransactions.reduce((sum, t) => sum + Math.abs(t.amount), 0))}
            </span>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Editor Modal -->
  {#if isEditing}
    <div
      class="modal-overlay"
      onclick={cancelEdit}
      onkeydown={(e) => e.key === "Escape" && cancelEdit()}
      role="dialog"
      aria-modal="true"
      tabindex="-1"
    >
      <div class="modal" onclick={(e) => e.stopPropagation()} role="document">
        <h3 class="modal-title">{editingCategory ? "Edit Category" : "Add Category"}</h3>

        <div class="form-group">
          <label for="cat-type">Type</label>
          <select id="cat-type" bind:value={editorForm.type}>
            <option value="income">Income</option>
            <option value="expense">Expense</option>
            <option value="savings">Savings</option>
          </select>
        </div>

        <div class="form-group">
          <label for="cat-name">Category Name</label>
          <input
            id="cat-name"
            type="text"
            bind:value={editorForm.category}
            placeholder="e.g., Groceries"
          />
        </div>

        <div class="form-group">
          <label for="cat-expected">Expected Amount</label>
          <input
            id="cat-expected"
            type="number"
            bind:value={editorForm.expected}
            min="0"
            step="100"
          />
        </div>

        <div class="form-group">
          <label for="cat-tags">Tags (comma-separated)</label>
          <input
            id="cat-tags"
            type="text"
            bind:value={editorForm.tags}
            placeholder="e.g., groceries, food, supermarket"
          />
          {#if allTags.length > 0}
            <div class="tag-suggestions">
              {#each allTags.slice(0, 20) as tag}
                <button
                  type="button"
                  class="tag-suggestion"
                  onclick={() => {
                    const current = editorForm.tags.split(",").map(t => t.trim()).filter(t => t);
                    if (!current.includes(tag)) {
                      editorForm.tags = [...current, tag].join(", ");
                    }
                  }}
                >
                  {tag}
                </button>
              {/each}
            </div>
          {/if}
        </div>

        <div class="form-group checkbox">
          <label>
            <input type="checkbox" bind:checked={editorForm.require_all} />
            Require ALL tags (AND logic)
          </label>
        </div>

        <div class="form-group">
          <label for="cat-sign">Amount Sign</label>
          <select id="cat-sign" bind:value={editorForm.amount_sign}>
            <option value={null}>Default ({editorForm.type === "income" ? "positive" : "negative"})</option>
            <option value="positive">Positive only</option>
            <option value="negative">Negative only</option>
            <option value="any">Any</option>
          </select>
        </div>

        <div class="modal-actions">
          <button class="btn secondary" onclick={cancelEdit}>Cancel</button>
          <button class="btn primary" onclick={saveCategory}>Save</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .budget-view {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
    overflow-y: auto;
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
    flex-wrap: wrap;
  }

  .title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .month-selector {
    padding: 4px 8px;
    font-size: 13px;
    background: var(--bg-primary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
  }

  .compare-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
  }

  .compare-vs {
    font-size: 12px;
    color: var(--text-muted);
  }

  .filter-btn {
    padding: 4px 12px;
    font-size: 12px;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    cursor: pointer;
  }

  .filter-btn:hover {
    background: var(--bg-primary);
    color: var(--text-primary);
  }

  .account-filter {
    margin-top: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--bg-primary);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-primary);
  }

  .filter-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-sm);
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .text-btn {
    background: none;
    border: none;
    color: var(--accent-primary);
    font-size: 11px;
    cursor: pointer;
  }

  .text-btn:hover {
    text-decoration: underline;
  }

  .account-list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  .account-option {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--text-primary);
    cursor: pointer;
  }

  .error-bar {
    padding: var(--spacing-sm) var(--spacing-lg);
    background: var(--accent-danger);
    color: white;
    font-size: 12px;
  }

  .loading {
    padding: var(--spacing-xl);
    text-align: center;
    color: var(--text-muted);
  }

  /* Hero Chart */
  .hero-chart {
    padding: var(--spacing-lg);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-primary);
  }

  .chart-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--spacing-md);
  }

  .chart-container {
    position: relative;
  }

  .chart {
    width: 100%;
    height: auto;
    max-height: 180px;
  }

  .axis-label {
    font-size: 10px;
    fill: var(--text-muted);
  }

  .month-label {
    font-size: 11px;
    fill: var(--text-muted);
    text-anchor: middle;
  }

  .month-label.selected {
    fill: var(--text-primary);
    font-weight: 600;
  }

  .chart-legend {
    display: flex;
    justify-content: center;
    gap: var(--spacing-lg);
    margin-top: var(--spacing-sm);
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--text-muted);
  }

  .legend-item .dot {
    width: 8px;
    height: 8px;
    border-radius: 2px;
  }

  .legend-item.income .dot {
    background: var(--accent-success, #22c55e);
  }

  .legend-item.expense .dot {
    background: var(--accent-danger, #ef4444);
  }

  .legend-item.savings .dot {
    background: var(--accent-primary);
  }

  /* Summary Cards */
  .summary-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-md);
    padding: var(--spacing-lg);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-primary);
  }

  .summary-card {
    padding: var(--spacing-md);
    background: var(--bg-primary);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-primary);
  }

  .card-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }

  .card-actual {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .card-expected {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
  }

  .card-compare {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
    font-style: italic;
  }

  .summary-card.income .card-actual {
    color: var(--accent-success, #22c55e);
  }

  .summary-card.expense .card-actual {
    color: var(--accent-danger, #ef4444);
  }

  .summary-card.savings .card-actual {
    color: var(--accent-primary);
  }

  .summary-card.net.positive .card-actual {
    color: var(--accent-success, #22c55e);
  }

  .summary-card.net.negative .card-actual {
    color: var(--accent-danger, #ef4444);
  }

  /* Budget Sections */
  .budget-sections {
    flex: 1;
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .budget-section {
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-primary);
    overflow: hidden;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-primary);
  }

  .section-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .add-btn {
    padding: 4px 12px;
    font-size: 12px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-weight: 600;
  }

  .add-btn:hover {
    opacity: 0.9;
  }

  .empty-section {
    padding: var(--spacing-lg);
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
  }

  .category-list {
    padding: var(--spacing-sm) 0;
  }

  .category-row {
    display: flex;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-lg);
    gap: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
    cursor: pointer;
    transition: background 0.15s;
  }

  .category-row:hover {
    background: var(--bg-tertiary);
  }

  .category-row:last-child {
    border-bottom: none;
  }

  .category-info {
    flex: 0 0 180px;
  }

  .category-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .category-tags {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .tag {
    padding: 1px 6px;
    background: var(--bg-tertiary);
    color: var(--text-muted);
    border-radius: 3px;
    font-size: 10px;
  }

  .tag-more {
    padding: 1px 6px;
    background: var(--bg-primary);
    color: var(--text-muted);
    border-radius: 3px;
    font-size: 10px;
  }

  .category-progress {
    flex: 1;
  }

  .progress-bar {
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 4px;
  }

  .progress-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .progress-text {
    font-size: 12px;
    font-family: var(--font-mono);
  }

  .progress-text .actual {
    color: var(--text-primary);
    font-weight: 600;
  }

  .progress-text .expected {
    color: var(--text-muted);
  }

  .progress-text .compare-value {
    color: var(--text-muted);
    font-style: italic;
    margin-left: 8px;
  }

  .progress-text .percent {
    color: var(--text-muted);
    margin-left: 8px;
  }

  .progress-text .percent.over {
    color: var(--accent-danger, #ef4444);
    font-weight: 600;
  }

  .category-actions {
    display: flex;
    gap: 8px;
    flex: 0 0 auto;
  }

  .action-btn {
    padding: 4px 8px;
    font-size: 11px;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    cursor: pointer;
  }

  .action-btn:hover {
    background: var(--bg-primary);
    color: var(--text-primary);
  }

  .action-btn.delete:hover {
    background: var(--accent-danger);
    color: white;
    border-color: var(--accent-danger);
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .modal {
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
    padding: var(--spacing-lg);
    width: 400px;
    max-width: 90vw;
    max-height: 90vh;
    overflow-y: auto;
  }

  .transactions-modal {
    width: 700px;
    padding: 0;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
  }

  .modal-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 24px;
    color: var(--text-muted);
    cursor: pointer;
    line-height: 1;
  }

  .close-btn:hover {
    color: var(--text-primary);
  }

  .modal-loading, .modal-empty {
    padding: var(--spacing-xl);
    text-align: center;
    color: var(--text-muted);
  }

  .transactions-list {
    max-height: 400px;
    overflow-y: auto;
  }

  .transaction-row {
    display: flex;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-lg);
    gap: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
    font-size: 13px;
  }

  .transaction-row:last-child {
    border-bottom: none;
  }

  .txn-date {
    flex: 0 0 90px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 12px;
  }

  .txn-desc {
    flex: 1;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .txn-account {
    flex: 0 0 120px;
    color: var(--text-muted);
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .txn-amount {
    flex: 0 0 80px;
    text-align: right;
    font-family: var(--font-mono);
    font-weight: 600;
    color: var(--text-primary);
  }

  .txn-amount.negative {
    color: var(--accent-danger, #ef4444);
  }

  .modal-footer {
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-lg);
    border-top: 1px solid var(--border-primary);
    background: var(--bg-tertiary);
    font-size: 12px;
    color: var(--text-muted);
  }

  .txn-total {
    font-weight: 600;
    color: var(--text-primary);
  }

  .form-group {
    margin-bottom: var(--spacing-md);
  }

  .form-group label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }

  .form-group input[type="text"],
  .form-group input[type="number"],
  .form-group select {
    width: 100%;
    padding: 8px 12px;
    font-size: 13px;
    background: var(--bg-primary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
  }

  .form-group input:focus,
  .form-group select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .form-group.checkbox label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .form-group.checkbox input[type="checkbox"] {
    width: auto;
  }

  .tag-suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 8px;
  }

  .tag-suggestion {
    padding: 2px 8px;
    font-size: 11px;
    background: var(--bg-tertiary);
    color: var(--text-muted);
    border: 1px solid var(--border-primary);
    border-radius: 3px;
    cursor: pointer;
  }

  .tag-suggestion:hover {
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-color: var(--accent-primary);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-lg);
  }

  .btn {
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    border-radius: var(--radius-sm);
    cursor: pointer;
    border: none;
  }

  .btn.primary {
    background: var(--accent-primary);
    color: var(--bg-primary);
  }

  .btn.primary:hover {
    opacity: 0.9;
  }

  .btn.secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
  }

  .btn.secondary:hover {
    background: var(--bg-primary);
  }

  /* Responsive */
  @media (max-width: 800px) {
    .summary-cards {
      grid-template-columns: repeat(2, 1fr);
    }

    .category-row {
      flex-wrap: wrap;
    }

    .category-info {
      flex: 1 1 100%;
    }

    .category-progress {
      flex: 1 1 100%;
    }

    .header-controls {
      width: 100%;
      justify-content: flex-start;
    }
  }
</style>
