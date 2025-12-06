<script lang="ts">
  /**
   * SaveAsRuleModal - Create an auto-tag rule from a tagging action
   *
   * Simple pattern matching by default with match type options,
   * SQL editing available for power users.
   */
  import { Modal } from "../../shared";
  import type { Transaction } from "./types";
  import type { TagRule, RuleTestResult } from "./rules";
  import {
    generateRuleId,
    saveRule,
    testSqlCondition,
    generateSqlFromTransactions,
  } from "./rules";

  interface Props {
    open: boolean;
    transactions: Transaction[];
    tags: string[];
    onclose: () => void;
    onsaved: () => void;
  }

  let { open, transactions, tags, onclose, onsaved }: Props = $props();

  // Match type options for simple mode
  type MatchType = "contains" | "starts_with" | "ends_with" | "exact" | "regex";

  const matchTypeLabels: Record<MatchType, string> = {
    contains: "Contains",
    starts_with: "Starts with",
    ends_with: "Ends with",
    exact: "Exact match",
    regex: "Regex",
  };

  // Form state
  let ruleName = $state("");
  let pattern = $state("");
  let matchType = $state<MatchType>("contains");
  let sqlCondition = $state("");
  let showSql = $state(false);
  let isTesting = $state(false);
  let testResult = $state<RuleTestResult | null>(null);
  let error = $state<string | null>(null);
  let isSaving = $state(false);

  // Track initialization and last tested value
  let lastInitializedFor = $state<string | null>(null);
  let lastTestedCondition = $state<string | null>(null);

  // Debounce timer for auto-preview
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  // Build SQL from pattern and match type
  function buildSqlFromPattern(pat: string, type: MatchType): string {
    if (!pat.trim()) return "";
    const escaped = pat.trim().replace(/'/g, "''");
    const lower = escaped.toLowerCase();

    switch (type) {
      case "contains":
        return `description ILIKE '%${lower}%'`;
      case "starts_with":
        return `description ILIKE '${lower}%'`;
      case "ends_with":
        return `description ILIKE '%${lower}'`;
      case "exact":
        return `description ILIKE '${lower}'`;
      case "regex":
        // Use 'i' option for case-insensitive regex matching
        return `regexp_matches(description, '${escaped}', 'i')`;
      default:
        return `description ILIKE '%${lower}%'`;
    }
  }

  // Computed SQL from pattern (when not in SQL mode)
  let effectiveSql = $derived.by(() => {
    if (showSql) {
      return sqlCondition;
    }
    return buildSqlFromPattern(pattern, matchType);
  });

  // Reset form when modal opens with new transactions
  $effect(() => {
    const txnKey = open ? transactions.map(t => t.transaction_id).join(",") : null;

    if (open && transactions.length > 0 && txnKey !== lastInitializedFor) {
      lastInitializedFor = txnKey;

      // Generate suggested pattern from transaction descriptions
      const descriptions = transactions.map(t => t.description);
      const suggestion = generateSqlFromTransactions(descriptions);

      pattern = suggestion.pattern || "";
      matchType = "contains";
      sqlCondition = suggestion.sql;
      showSql = false;

      // Generate rule name from pattern and tags
      if (suggestion.pattern) {
        ruleName = `Tag "${suggestion.pattern}" as ${tags.join(", ")}`;
      } else {
        ruleName = `Tag as ${tags.join(", ")}`;
      }

      testResult = null;
      error = null;
      lastTestedCondition = null;

      // Auto-test the initial condition
      if (suggestion.sql) {
        runTest(suggestion.sql);
      }
    } else if (!open) {
      lastInitializedFor = null;
      lastTestedCondition = null;
    }
  });

  // SQL-specific error (shown inline, less jarring)
  let sqlError = $state<string | null>(null);

  async function runTest(sql: string, force = false) {
    if (!sql.trim()) {
      testResult = null;
      sqlError = null;
      return;
    }

    if (!force && sql === lastTestedCondition) {
      return;
    }

    sqlError = null;
    isTesting = true;
    lastTestedCondition = sql;

    try {
      testResult = await testSqlCondition(sql, 200);
    } catch (e) {
      sqlError = e instanceof Error ? e.message : "Invalid condition";
      // Keep previous results visible so the UI doesn't flash
    } finally {
      isTesting = false;
    }
  }

  function scheduleTest() {
    // Clear any pending debounce
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    const sql = effectiveSql;
    if (!sql.trim()) {
      testResult = null;
      return;
    }

    // Debounce: wait 300ms before running test
    debounceTimer = setTimeout(() => {
      runTest(sql);
    }, 300);
  }

  function runTestNow() {
    // Clear any pending debounce and run immediately
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    const sql = effectiveSql;
    if (sql) {
      runTest(sql, true);
    }
  }

  function handleInput() {
    // Schedule debounced test on any input change
    scheduleTest();
  }

  function handleInputKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      runTestNow();
    }
  }

  function handleMatchTypeChange() {
    // Immediately run test when match type changes (no debounce needed)
    lastTestedCondition = null;
    const sql = effectiveSql;
    if (sql) {
      runTest(sql);
    }
  }

  function toggleSqlMode() {
    if (!showSql) {
      // Switching to SQL mode - initialize with current effective SQL
      sqlCondition = effectiveSql;
    }
    showSql = !showSql;

    // Immediately run test when switching modes
    lastTestedCondition = null;
    const sql = showSql ? sqlCondition : buildSqlFromPattern(pattern, matchType);
    if (sql) {
      runTest(sql);
    }
  }

  async function handleSave() {
    const sql = effectiveSql;

    if (!sql.trim()) {
      error = "Enter a pattern to match";
      return;
    }

    if (!ruleName.trim()) {
      error = "Enter a rule name";
      return;
    }

    error = null;
    isSaving = true;

    try {
      const rule: TagRule = {
        id: generateRuleId(),
        name: ruleName.trim(),
        sqlCondition: sql.trim(),
        conditions: [],
        conditionLogic: "all",
        tags,
        enabled: true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      await saveRule(rule);
      onsaved();
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to save rule";
    } finally {
      isSaving = false;
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      onclose();
    }
  }

  // Available columns for SQL reference
  const columns = [
    { name: "description", type: "VARCHAR", example: "description ILIKE '%starbucks%'" },
    { name: "amount", type: "DECIMAL", example: "amount < -50" },
    { name: "account_name", type: "VARCHAR", example: "account_name = 'Checking'" },
    { name: "transaction_date", type: "DATE", example: "transaction_date >= '2024-01-01'" },
  ];

  // Common filters that users can click to insert
  const commonFilters = [
    { label: "Contains", sql: "description ILIKE '%keyword%'" },
    { label: "Starts with", sql: "description ILIKE 'keyword%'" },
    { label: "Amount >", sql: "amount > 100" },
    { label: "Amount <", sql: "amount < -50" },
    { label: "Regex", sql: "regexp_matches(description, 'pattern', 'i')" },
    { label: "Date after", sql: "transaction_date >= '2024-01-01'" },
  ];

  function insertFilter(sql: string) {
    sqlCondition = sql;
    // Immediately test the inserted filter
    lastTestedCondition = null;
    runTest(sql);
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div onkeydown={handleKeyDown}>
  <Modal {open} title="Save as Auto-Tag Rule" {onclose} width="600px">
    <div class="modal-content">
      <!-- Summary -->
      <div class="summary-section">
        <p class="summary-text">
          You tagged <strong>{transactions.length}</strong> transaction{transactions.length > 1 ? "s" : ""} with:
        </p>
        <div class="tags-preview">
          {#each tags as tag}
            <span class="tag">{tag}</span>
          {/each}
        </div>
      </div>

      {#if error}
        <div class="form-error">{error}</div>
      {/if}

      <!-- Rule Name -->
      <div class="form-group">
        <label for="rule-name">Rule Name</label>
        <input
          id="rule-name"
          type="text"
          bind:value={ruleName}
          placeholder="e.g., Tag Starbucks as coffee"
        />
      </div>

      <!-- Pattern or SQL Condition -->
      <div class="form-group">
        <div class="condition-header">
          <label for="condition-input">
            {showSql ? "SQL WHERE Clause" : "Match description"}
          </label>
          <button class="toggle-sql" onclick={toggleSqlMode}>
            {showSql ? "Simple mode" : "Edit SQL"}
          </button>
        </div>

        {#if showSql}
          <div class="sql-input-wrapper" class:has-error={sqlError}>
            <textarea
              id="condition-input"
              bind:value={sqlCondition}
              oninput={handleInput}
              onkeydown={handleInputKeyDown}
              placeholder="description ILIKE '%merchant%'"
              rows="3"
              spellcheck="false"
              class:error={sqlError}
            ></textarea>
            {#if sqlError}
              <div class="sql-error-tooltip" title={sqlError}>
                <span class="error-icon">!</span>
              </div>
            {/if}
          </div>

          <!-- Common filters -->
          <div class="common-filters">
            <span class="filters-label">Insert:</span>
            {#each commonFilters as filter}
              <button class="filter-chip" onclick={() => insertFilter(filter.sql)}>
                {filter.label}
              </button>
            {/each}
          </div>

          <div class="sql-help">
            <details open>
              <summary>Available columns</summary>
              <div class="columns-list">
                {#each columns as col}
                  <div class="column-item">
                    <code>{col.name}</code>
                    <span class="column-type">{col.type}</span>
                    <span class="column-example">{col.example}</span>
                  </div>
                {/each}
              </div>
              <p class="sql-tip">
                Use <code>ILIKE</code> for case-insensitive matching.
                Use <code>regexp_matches(str, pattern, 'i')</code> for regex.
              </p>
            </details>
          </div>
        {:else}
          <div class="pattern-input-row">
            <div class="match-type-buttons">
              {#each Object.entries(matchTypeLabels) as [value, label]}
                <button
                  class="match-type-btn"
                  class:active={matchType === value}
                  onclick={() => { matchType = value as MatchType; handleMatchTypeChange(); }}
                >
                  {label}
                </button>
              {/each}
            </div>
            <input
              id="condition-input"
              type="text"
              bind:value={pattern}
              oninput={handleInput}
              onkeydown={handleInputKeyDown}
              placeholder={matchType === "regex" ? "e.g., starbucks|coffee" : "e.g., STARBUCKS"}
            />
          </div>
          <p class="pattern-hint">
            {#if matchType === "contains"}
              Matches any transaction with this text anywhere in the description.
            {:else if matchType === "starts_with"}
              Matches transactions where the description begins with this text.
            {:else if matchType === "ends_with"}
              Matches transactions where the description ends with this text.
            {:else if matchType === "exact"}
              Matches transactions with exactly this description.
            {:else if matchType === "regex"}
              Matches using a regular expression pattern. Use <code>|</code> for OR, <code>.*</code> for wildcards.
            {/if}
            <span class="case-note">Case-insensitive.</span>
          </p>
        {/if}
      </div>

      <!-- Test Results -->
      {#if testResult || isTesting}
        <div class="test-results" class:has-matches={testResult && testResult.matchingCount > 0} class:loading={isTesting}>
          <div class="test-header">
            <span class="test-count">
              {#if isTesting && !testResult}
                Testing...
              {:else if testResult}
                {testResult.matchingCount} matching transaction{testResult.matchingCount !== 1 ? "s" : ""}
                {#if isTesting}<span class="updating">updating...</span>{/if}
              {/if}
            </span>
          </div>
          {#if testResult && testResult.sampleMatches.length > 0}
            <div class="test-samples">
              {#each testResult.sampleMatches as match}
                <div class="test-sample">
                  <span class="sample-desc">{match.description}</span>
                  <span class="sample-amount" class:negative={match.amount < 0} class:positive={match.amount >= 0}>
                    {match.amount < 0 ? '-' : ''}${Math.abs(match.amount).toFixed(2)}
                  </span>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </div>

    {#snippet actions()}
      <button class="btn secondary" onclick={onclose}>Cancel</button>
      <button
        class="btn primary"
        onclick={handleSave}
        disabled={isSaving || !effectiveSql.trim()}
      >
        {isSaving ? "Saving..." : "Save Rule"}
      </button>
    {/snippet}
  </Modal>
</div>

<style>
  .modal-content {
    padding: var(--spacing-md) var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .summary-section {
    padding: var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: 6px;
  }

  .summary-text {
    margin: 0 0 var(--spacing-sm);
    font-size: 13px;
    color: var(--text-primary);
  }

  .tags-preview {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .tag {
    padding: 4px 10px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }

  .form-error {
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--accent-danger, #ef4444);
    border-radius: 4px;
    color: var(--accent-danger, #ef4444);
    font-size: 13px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .condition-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .condition-header label {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
  }

  .toggle-sql {
    background: none;
    border: none;
    color: var(--accent-primary);
    font-size: 11px;
    cursor: pointer;
    text-decoration: underline;
    padding: 0;
  }

  .toggle-sql:hover {
    color: var(--text-primary);
  }

  .form-group label {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
  }

  .form-group input {
    padding: 8px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
  }

  .form-group input:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .form-group textarea {
    padding: 10px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
    font-family: var(--font-mono, monospace);
    resize: vertical;
    min-height: 60px;
  }

  .form-group textarea:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .sql-input-wrapper {
    position: relative;
  }

  .sql-input-wrapper textarea.error {
    border-color: var(--accent-danger, #ef4444);
  }

  .sql-error-tooltip {
    position: absolute;
    top: 8px;
    right: 8px;
    cursor: help;
  }

  .error-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    background: var(--accent-danger, #ef4444);
    color: white;
    font-size: 12px;
    font-weight: 700;
    border-radius: 50%;
  }

  .pattern-input-row {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .match-type-buttons {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .match-type-btn {
    padding: 4px 10px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    font-size: 11px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .match-type-btn:hover {
    background: var(--bg-secondary);
    border-color: var(--text-muted);
  }

  .match-type-btn.active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: var(--bg-primary);
  }

  .pattern-hint {
    margin: 0;
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.4;
  }

  .pattern-hint code {
    background: var(--bg-tertiary);
    padding: 1px 4px;
    border-radius: 2px;
    font-family: var(--font-mono, monospace);
    font-size: 10px;
  }

  .case-note {
    opacity: 0.7;
  }

  .sql-help {
    margin-top: 4px;
  }

  .sql-help details {
    font-size: 12px;
    color: var(--text-muted);
  }

  .sql-help summary {
    cursor: pointer;
    user-select: none;
  }

  .sql-help summary:hover {
    color: var(--text-primary);
  }

  .columns-list {
    margin-top: var(--spacing-sm);
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: var(--spacing-sm);
    background: var(--bg-tertiary);
    border-radius: 4px;
  }

  .column-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 11px;
  }

  .column-item code {
    background: var(--bg-primary);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: var(--font-mono, monospace);
    color: var(--accent-primary);
  }

  .column-type {
    color: var(--text-muted);
    opacity: 0.7;
    min-width: 60px;
  }

  .column-example {
    color: var(--text-muted);
    font-family: var(--font-mono, monospace);
    font-size: 10px;
  }

  .sql-tip {
    margin: var(--spacing-sm) 0 0;
    font-size: 11px;
    color: var(--text-muted);
  }

  .sql-tip code {
    background: var(--bg-tertiary);
    padding: 1px 4px;
    border-radius: 2px;
    font-family: var(--font-mono, monospace);
  }

  .test-results {
    padding: var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: 6px;
    border: 1px solid var(--border-primary);
  }

  .test-results.loading {
    opacity: 0.8;
  }

  .updating {
    font-size: 11px;
    font-weight: 400;
    color: var(--text-muted);
    margin-left: var(--spacing-sm);
  }

  .test-results.has-matches {
    border-color: var(--accent-success, #22c55e);
  }

  .test-header {
    margin-bottom: var(--spacing-sm);
  }

  .test-count {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .test-samples {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 300px;
    overflow-y: auto;
  }

  .test-sample {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 8px;
    background: var(--bg-primary);
    border-radius: 4px;
    font-size: 12px;
  }

  .sample-desc {
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    margin-right: var(--spacing-sm);
  }

  .sample-amount {
    color: var(--text-muted);
    font-family: var(--font-mono, monospace);
    flex-shrink: 0;
  }

  .sample-amount.negative {
    color: var(--accent-danger);
  }

  .sample-amount.positive {
    color: var(--accent-success, #22c55e);
  }

  .common-filters {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: var(--spacing-sm);
  }

  .filters-label {
    font-size: 11px;
    color: var(--text-muted);
  }

  .filter-chip {
    padding: 3px 8px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    font-size: 10px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .filter-chip:hover {
    background: var(--bg-secondary);
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }
</style>
