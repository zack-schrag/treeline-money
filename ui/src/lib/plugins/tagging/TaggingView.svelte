<script lang="ts">
  import { onMount } from "svelte";
  import { executeQuery } from "../../sdk";
  import { FrequencyBasedSuggester, type TagSuggestion, type Transaction } from "./suggestions";

  // Initialize suggester
  const suggester = new FrequencyBasedSuggester();

  let transactions = $state<Transaction[]>([]);
  let suggestions = $state<Map<string, TagSuggestion[]>>(new Map());
  let isLoading = $state(true);
  let error = $state<string | null>(null);

  // Selection state
  let selectedIndices = $state<Set<number>>(new Set());
  let cursorIndex = $state(0);

  // Filter state
  let filterMode = $state<"all" | "untagged">("untagged");
  let searchQuery = $state("");
  let isSearching = $state(false);
  let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  // Custom tag input mode (for typing a new tag)
  let isCustomTagging = $state(false);
  let customTagInput = $state("");

  // Element refs
  let customTagInputEl: HTMLInputElement | null = null;
  let searchInputEl: HTMLInputElement | null = null;
  let containerEl: HTMLDivElement | null = null;

  // Suggestions for current transaction
  let currentSuggestions = $derived.by(() => {
    const txn = transactions[cursorIndex];
    if (!txn) return [];
    return suggestions.get(txn.transaction_id) || [];
  });

  async function loadTransactions() {
    isLoading = true;
    error = null;

    try {
      let query = `
        SELECT
          transaction_id,
          transaction_date,
          description,
          amount,
          tags,
          account_name
        FROM transactions
      `;

      if (filterMode === "untagged" && !searchQuery.trim()) {
        query += " WHERE tags = []";
      } else if (searchQuery.trim()) {
        const escapedSearch = searchQuery.trim().replace(/'/g, "''");
        query += ` WHERE description ILIKE '%${escapedSearch}%'`;
      }

      query += " ORDER BY transaction_date DESC LIMIT 500";

      const result = await executeQuery(query);

      transactions = result.rows.map(row => ({
        transaction_id: row[0] as string,
        transaction_date: row[1] as string,
        description: row[2] as string,
        amount: row[3] as number,
        tags: (row[4] as string[]) || [],
        account_name: row[5] as string,
      }));

      // Reset cursor if out of bounds
      if (cursorIndex >= transactions.length) {
        cursorIndex = Math.max(0, transactions.length - 1);
      }

      // Compute suggestions for all loaded transactions
      suggestions = await suggester.suggestBatch(transactions, 9);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load transactions";
      console.error("Failed to load transactions:", e);
    } finally {
      isLoading = false;
    }
  }

  function handleSearchInput() {
    // Debounced live search
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
    }
    searchDebounceTimer = setTimeout(() => {
      loadTransactions();
    }, 150);
  }

  function handleKeyDown(e: KeyboardEvent) {
    // Search mode - only handle escape, let typing flow through
    if (isSearching) {
      if (e.key === "Escape") {
        e.preventDefault();
        exitSearch();
      }
      return;
    }

    // Custom tag input mode
    if (isCustomTagging) {
      handleCustomTagKeyDown(e);
      return;
    }

    // Number keys 1-9 to apply suggested tags
    if (e.key >= "1" && e.key <= "9") {
      const tagIndex = parseInt(e.key) - 1;
      if (tagIndex < currentSuggestions.length) {
        e.preventDefault();
        applyTagToCurrentOrSelected(currentSuggestions[tagIndex].tag);
      }
      return;
    }

    // Normal navigation mode
    switch(e.key) {
      case "j":
      case "ArrowDown":
        e.preventDefault();
        moveCursor(1);
        break;
      case "k":
      case "ArrowUp":
        e.preventDefault();
        moveCursor(-1);
        break;
      case " ":
        e.preventDefault();
        toggleSelection();
        break;
      case "x":
        e.preventDefault();
        toggleSelectionNoMove();
        break;
      case "a":
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          selectAll();
        }
        break;
      case "A":
        e.preventDefault();
        selectAll();
        break;
      case "Escape":
        e.preventDefault();
        deselectAll();
        break;
      case "t":
        e.preventDefault();
        startCustomTagging();
        break;
      case "r":
        e.preventDefault();
        removeTagsFromCurrent();
        break;
      case "u":
        e.preventDefault();
        filterMode = "untagged";
        searchQuery = "";
        loadTransactions();
        break;
      case "*":
        e.preventDefault();
        filterMode = "all";
        searchQuery = "";
        loadTransactions();
        break;
      case "/":
        e.preventDefault();
        startSearch();
        break;
      case "g":
        e.preventDefault();
        cursorIndex = 0;
        scrollToCursor();
        break;
      case "G":
        e.preventDefault();
        cursorIndex = transactions.length - 1;
        scrollToCursor();
        break;
      case "n":
        e.preventDefault();
        skipToNextUntagged();
        break;
    }
  }

  function handleCustomTagKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      cancelCustomTagging();
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      applyCustomTag();
      return;
    }

    if (e.key === "Tab") {
      e.preventDefault();
      // Autocomplete from suggestions
      const input = customTagInput.toLowerCase().trim();
      if (input) {
        const match = currentSuggestions.find(s => s.tag.toLowerCase().startsWith(input));
        if (match) {
          customTagInput = match.tag;
        }
      }
      return;
    }
  }

  function startSearch() {
    isSearching = true;
    filterMode = "all";
    setTimeout(() => searchInputEl?.focus(), 10);
  }

  function exitSearch() {
    isSearching = false;
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
    }
    containerEl?.focus();
  }

  function clearSearch() {
    searchQuery = "";
    filterMode = "untagged";
    loadTransactions();
  }

  function moveCursor(delta: number) {
    const newIndex = cursorIndex + delta;
    if (newIndex >= 0 && newIndex < transactions.length) {
      cursorIndex = newIndex;
      scrollToCursor();
    }
  }

  function skipToNextUntagged() {
    for (let i = cursorIndex + 1; i < transactions.length; i++) {
      if (transactions[i].tags.length === 0) {
        cursorIndex = i;
        scrollToCursor();
        return;
      }
    }
    for (let i = 0; i < cursorIndex; i++) {
      if (transactions[i].tags.length === 0) {
        cursorIndex = i;
        scrollToCursor();
        return;
      }
    }
  }

  function scrollToCursor() {
    setTimeout(() => {
      const element = document.querySelector(`[data-index="${cursorIndex}"]`);
      if (element) {
        element.scrollIntoView({ block: "nearest", behavior: "auto" });
      }
    }, 0);
  }

  function toggleSelection() {
    toggleSelectionNoMove();
    moveCursor(1);
  }

  function toggleSelectionNoMove() {
    if (selectedIndices.has(cursorIndex)) {
      selectedIndices.delete(cursorIndex);
    } else {
      selectedIndices.add(cursorIndex);
    }
    selectedIndices = new Set(selectedIndices);
  }

  function selectAll() {
    selectedIndices = new Set(transactions.map((_, i) => i));
  }

  function deselectAll() {
    selectedIndices = new Set();
  }

  function getSelectedTransactions(): Transaction[] {
    if (selectedIndices.size === 0) {
      const current = transactions[cursorIndex];
      return current ? [current] : [];
    }
    return Array.from(selectedIndices).map(i => transactions[i]).filter(Boolean);
  }

  async function applyTagToCurrentOrSelected(tag: string) {
    const selected = getSelectedTransactions();
    if (selected.length === 0) return;

    try {
      // Update each transaction's tags via SQL
      for (const txn of selected) {
        const currentTags = txn.tags || [];
        if (currentTags.includes(tag)) continue;

        const newTags = [...currentTags, tag];
        const tagsJson = JSON.stringify(newTags);
        const escapedId = txn.transaction_id.replace(/'/g, "''");

        await executeQuery(
          `UPDATE sys_transactions SET tags = '${tagsJson}' WHERE transaction_id = '${escapedId}'`,
          { readonly: false }
        );
      }

      deselectAll();
      await loadTransactions();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to apply tag";
      console.error("Failed to apply tag:", e);
    }
  }

  function startCustomTagging() {
    if (transactions.length === 0) return;
    isCustomTagging = true;
    customTagInput = "";
    setTimeout(() => customTagInputEl?.focus(), 10);
  }

  function cancelCustomTagging() {
    isCustomTagging = false;
    customTagInput = "";
    containerEl?.focus();
  }

  async function applyCustomTag() {
    const tag = customTagInput.trim();
    if (!tag) {
      cancelCustomTagging();
      return;
    }

    cancelCustomTagging();
    await applyTagToCurrentOrSelected(tag);
  }

  async function removeTagsFromCurrent() {
    const selected = getSelectedTransactions();
    if (selected.length === 0) return;

    const tagsToRemove = [...new Set(selected.flatMap(t => t.tags || []))];
    if (tagsToRemove.length === 0) return;

    try {
      for (const txn of selected) {
        const escapedId = txn.transaction_id.replace(/'/g, "''");
        await executeQuery(
          `UPDATE sys_transactions SET tags = '[]' WHERE transaction_id = '${escapedId}'`,
          { readonly: false }
        );
      }

      deselectAll();
      await loadTransactions();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to remove tags";
      console.error("Failed to remove tags:", e);
    }
  }

  onMount(() => {
    loadTransactions();
    containerEl?.focus();
  });

  function getTargetCount(): number {
    return selectedIndices.size || 1;
  }

  let currentTxn = $derived(transactions[cursorIndex]);
</script>

<div
  class="tagging-view"
  bind:this={containerEl}
  tabindex="0"
  onkeydown={handleKeyDown}
>
  <!-- Header -->
  <div class="header">
    <div class="title-row">
      <h1 class="title">Tag Transactions</h1>
      <div class="mode-indicator">
        {#if searchQuery}
          <span class="mode search-mode">Search</span>
          <span class="search-term">"{searchQuery}"</span>
          <button class="clear-search" onclick={clearSearch}>x</button>
        {:else if filterMode === "untagged"}
          <span class="mode">Untagged</span>
        {:else}
          <span class="mode">All</span>
        {/if}
      </div>
    </div>
    <div class="stats">
      <span>{transactions.length} transactions</span>
      {#if selectedIndices.size > 0}
        <span class="selected-count">* {selectedIndices.size} selected</span>
      {/if}
    </div>
  </div>

  <!-- Help bar -->
  <div class="help-bar">
    <span><kbd>j</kbd><kbd>k</kbd> nav</span>
    <span><kbd>1-9</kbd> apply tag</span>
    <span><kbd>t</kbd> custom tag</span>
    <span><kbd>space</kbd> select</span>
    <span><kbd>r</kbd> remove</span>
    <span><kbd>/</kbd> search</span>
    <span><kbd>u</kbd> untagged</span>
    <span><kbd>n</kbd> next untagged</span>
  </div>

  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  <!-- Main content area: list + sidebar -->
  <div class="main-content">
    <!-- Transaction list -->
    <div class="list-container">
      {#if isLoading}
        <div class="empty-state">Loading...</div>
      {:else if transactions.length === 0}
        <div class="empty-state">
          {#if filterMode === "untagged"}
            All caught up! No untagged transactions.
          {:else}
            No transactions found.
          {/if}
        </div>
      {:else}
        {#each transactions as txn, index}
          <div
            class="row"
            class:cursor={cursorIndex === index}
            class:selected={selectedIndices.has(index)}
            data-index={index}
          >
            <div class="row-select">
              {#if selectedIndices.has(index)}
                <span class="checkmark">+</span>
              {:else}
                <span class="dot">-</span>
              {/if}
            </div>
            <div class="row-date">{txn.transaction_date}</div>
            <div class="row-desc">{txn.description}</div>
            <div class="row-amount" class:negative={txn.amount < 0}>
              {txn.amount < 0 ? '-' : ''}${Math.abs(txn.amount).toFixed(2)}
            </div>
            <div class="row-tags">
              {#if txn.tags.length === 0}
                <span class="no-tags">--</span>
              {:else}
                {#each txn.tags as tag}
                  <span class="tag">{tag}</span>
                {/each}
              {/if}
            </div>
          </div>
        {/each}
      {/if}
    </div>

    <!-- Sidebar: suggested tags (always visible) -->
    <div class="sidebar">
      <div class="sidebar-section">
        <div class="sidebar-title">Quick Tags</div>
        {#if currentSuggestions.length === 0}
          <div class="sidebar-empty">No suggestions</div>
        {:else}
          <div class="tag-suggestions">
            {#each currentSuggestions as suggestion, i}
              <button
                class="tag-suggestion"
                onclick={() => applyTagToCurrentOrSelected(suggestion.tag)}
              >
                <span class="tag-shortcut">{i + 1}</span>
                <span class="tag-name">{suggestion.tag}</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      {#if currentTxn && currentTxn.tags.length > 0}
        <div class="sidebar-section">
          <div class="sidebar-title">Current Tags</div>
          <div class="current-tags">
            {#each currentTxn.tags as tag}
              <span class="current-tag">{tag}</span>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Command bar (bottom) -->
  <div class="command-bar" class:active={isSearching || isCustomTagging}>
    {#if isSearching}
      <div class="command-input-row">
        <span class="command-prefix">/</span>
        <input
          bind:this={searchInputEl}
          type="text"
          class="command-input"
          bind:value={searchQuery}
          oninput={handleSearchInput}
          placeholder="search description... (live)"
        />
        <span class="command-hint">Esc to exit</span>
      </div>
    {:else if isCustomTagging}
      <div class="command-input-row">
        <span class="command-prefix">tag ({getTargetCount()}):</span>
        <input
          bind:this={customTagInputEl}
          type="text"
          class="command-input"
          bind:value={customTagInput}
          placeholder="enter tag name"
        />
        <span class="command-hint">Enter to apply, Tab to complete, Esc to cancel</span>
      </div>
    {:else}
      <div class="command-hint-row">
        <kbd>1-9</kbd> apply tag | <kbd>t</kbd> custom | <kbd>/</kbd> search
      </div>
    {/if}
  </div>
</div>

<style>
  .tagging-view {
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
    gap: var(--spacing-md);
  }

  .title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .mode-indicator {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .mode {
    font-size: 11px;
    padding: 2px 8px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-radius: 3px;
    font-weight: 600;
  }

  .mode.search-mode {
    background: var(--accent-warning, #f59e0b);
  }

  .search-term {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .clear-search {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
    padding: 2px 6px;
  }

  .clear-search:hover {
    color: var(--text-primary);
  }

  .stats {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .selected-count {
    color: var(--accent-primary);
    font-weight: 600;
  }

  .help-bar {
    padding: 6px var(--spacing-lg);
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-primary);
    display: flex;
    gap: var(--spacing-lg);
    font-size: 11px;
    color: var(--text-muted);
    flex-wrap: wrap;
  }

  .help-bar kbd {
    display: inline-block;
    padding: 1px 4px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 10px;
    margin-right: 2px;
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

  .sidebar {
    width: 200px;
    flex-shrink: 0;
    border-left: 1px solid var(--border-primary);
    background: var(--bg-secondary);
    padding: var(--spacing-md);
    overflow-y: auto;
  }

  .sidebar-section {
    margin-bottom: var(--spacing-lg);
  }

  .sidebar-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--spacing-sm);
  }

  .sidebar-empty {
    font-size: 12px;
    color: var(--text-muted);
    font-style: italic;
  }

  .tag-suggestions {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .tag-suggestion {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    font-size: 12px;
  }

  .tag-suggestion:hover {
    background: var(--bg-tertiary);
    border-color: var(--accent-primary);
  }

  .tag-shortcut {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    font-family: var(--font-mono);
    flex-shrink: 0;
  }

  .tag-name {
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .current-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .current-tag {
    padding: 2px 6px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
  }

  .empty-state {
    padding: var(--spacing-xl);
    text-align: center;
    color: var(--text-muted);
  }

  .row {
    display: flex;
    align-items: center;
    padding: 6px var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
    gap: var(--spacing-md);
  }

  .row.cursor {
    background: var(--bg-tertiary);
    border-left: 3px solid var(--accent-primary);
    padding-left: calc(var(--spacing-lg) - 3px);
  }

  .row.selected {
    background: rgba(var(--accent-primary-rgb, 99, 102, 241), 0.15);
  }

  .row.cursor.selected {
    background: rgba(var(--accent-primary-rgb, 99, 102, 241), 0.25);
  }

  .row-select {
    width: 16px;
    text-align: center;
    flex-shrink: 0;
  }

  .checkmark {
    color: var(--accent-primary);
    font-weight: bold;
  }

  .dot {
    color: var(--text-muted);
  }

  .row-date {
    width: 90px;
    flex-shrink: 0;
    color: var(--text-muted);
    font-size: 12px;
  }

  .row-desc {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-primary);
  }

  .row-amount {
    width: 90px;
    text-align: right;
    flex-shrink: 0;
    color: var(--text-secondary);
  }

  .row-amount.negative {
    color: var(--accent-danger);
  }

  .row-tags {
    width: 150px;
    flex-shrink: 0;
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .no-tags {
    color: var(--text-muted);
  }

  .tag {
    padding: 1px 6px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
  }

  .command-bar {
    border-top: 1px solid var(--border-primary);
    background: var(--bg-secondary);
    min-height: 36px;
  }

  .command-bar.active {
    background: var(--bg-tertiary);
  }

  .command-input-row {
    display: flex;
    align-items: center;
    padding: 6px var(--spacing-lg);
    gap: var(--spacing-sm);
  }

  .command-prefix {
    color: var(--accent-primary);
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 13px;
  }

  .command-input {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: 13px;
    outline: none;
  }

  .command-input::placeholder {
    color: var(--text-muted);
  }

  .command-hint {
    font-size: 11px;
    color: var(--text-muted);
  }

  .command-hint-row {
    padding: 8px var(--spacing-lg);
    font-size: 12px;
    color: var(--text-muted);
  }

  .command-hint-row kbd {
    display: inline-block;
    padding: 1px 4px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 10px;
  }
</style>
