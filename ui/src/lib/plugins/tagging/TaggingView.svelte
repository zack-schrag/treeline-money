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

  // Filter state - default to "all"
  let filterMode = $state<"all" | "untagged">("all");
  let searchQuery = $state("");
  let isSearching = $state(false);
  let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  // Custom tag input mode (for typing a new tag)
  let isCustomTagging = $state(false);
  let customTagInput = $state("");

  // Bulk tag mode
  let isBulkTagging = $state(false);
  let bulkTagInput = $state("");

  // Element refs
  let customTagInputEl: HTMLInputElement | null = null;
  let bulkTagInputEl: HTMLInputElement | null = null;
  let searchInputEl: HTMLInputElement | null = null;
  let containerEl: HTMLDivElement | null = null;

  // Suggestions for current transaction
  let currentSuggestions = $derived.by(() => {
    const txn = transactions[cursorIndex];
    if (!txn) return [];
    return suggestions.get(txn.transaction_id) || [];
  });

  // Stats
  let taggedCount = $derived(transactions.filter(t => t.tags.length > 0).length);

  // All known tags for autocomplete
  let allTags = $state<string[]>([]);

  // Autocomplete for custom tag input
  let tagAutocomplete = $derived.by(() => {
    if (!customTagInput || allTags.length === 0) return "";

    // Get the partial tag being typed (after last comma)
    const parts = customTagInput.split(",");
    const partial = parts[parts.length - 1].trim().toLowerCase();
    if (!partial) return "";

    // Find first matching tag from all known tags
    for (const tag of allTags) {
      if (tag.toLowerCase().startsWith(partial) && tag.toLowerCase() !== partial) {
        return tag.slice(partial.length);
      }
    }
    return "";
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
        // Search across description, account_name, amount (as string), and tags
        query += ` WHERE (
          description ILIKE '%${escapedSearch}%'
          OR account_name ILIKE '%${escapedSearch}%'
          OR CAST(amount AS VARCHAR) LIKE '%${escapedSearch}%'
          OR array_to_string(tags, ',') ILIKE '%${escapedSearch}%'
        )`;
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
    // Debounced live search - longer delay so typing feels instant
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
    }
    searchDebounceTimer = setTimeout(() => {
      loadTransactions();
    }, 400);
  }

  function handleSearchKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      // Immediately execute search and exit search mode
      if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
      }
      loadTransactions();
      exitSearch();
    } else if (e.key === "Escape") {
      e.preventDefault();
      exitSearch();
    }
    // Let all other keys flow through naturally
  }

  function handleKeyDown(e: KeyboardEvent) {
    // Search mode - handled separately
    if (isSearching) {
      return;
    }

    // Custom tag input mode
    if (isCustomTagging) {
      handleCustomTagKeyDown(e);
      return;
    }

    // Bulk tag input mode
    if (isBulkTagging) {
      handleBulkTagKeyDown(e);
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
        } else {
          // Bulk tag mode
          e.preventDefault();
          startBulkTagging();
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
      case "c":
        e.preventDefault();
        clearTagsFromCurrent();
        break;
      case "r":
        e.preventDefault();
        resetFilters();
        break;
      case "u":
        e.preventDefault();
        toggleFilterMode();
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
      case "[":
        e.preventDefault();
        pageUp();
        break;
      case "]":
        e.preventDefault();
        pageDown();
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
      // Apply autocomplete suggestion
      if (tagAutocomplete) {
        customTagInput += tagAutocomplete;
      }
      return;
    }
  }

  function handleBulkTagKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      cancelBulkTagging();
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      applyBulkTag();
      return;
    }

    if (e.key === "Tab") {
      e.preventDefault();
      // Autocomplete from suggestions
      const input = bulkTagInput.toLowerCase().trim();
      if (input) {
        const match = currentSuggestions.find(s => s.tag.toLowerCase().startsWith(input));
        if (match) {
          bulkTagInput = match.tag;
        }
      }
      return;
    }
  }

  function startSearch() {
    isSearching = true;
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
    loadTransactions();
    containerEl?.focus();
  }

  function toggleFilterMode() {
    filterMode = filterMode === "all" ? "untagged" : "all";
    loadTransactions();
  }

  function resetFilters() {
    searchQuery = "";
    filterMode = "all";
    loadTransactions();
  }

  function moveCursor(delta: number) {
    const newIndex = cursorIndex + delta;
    if (newIndex >= 0 && newIndex < transactions.length) {
      cursorIndex = newIndex;
      scrollToCursor();
    }
  }

  function pageUp() {
    cursorIndex = Math.max(0, cursorIndex - 20);
    scrollToCursor();
  }

  function pageDown() {
    cursorIndex = Math.min(transactions.length - 1, cursorIndex + 20);
    scrollToCursor();
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

  function handleRowClick(index: number) {
    cursorIndex = index;
    containerEl?.focus();
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

  function getSelectedIndicesArray(): number[] {
    if (selectedIndices.size === 0) {
      return [cursorIndex];
    }
    return Array.from(selectedIndices);
  }

  // Optimistic update: apply tag locally then persist in background
  async function applyTagToCurrentOrSelected(tag: string) {
    const indices = getSelectedIndicesArray();
    if (indices.length === 0) return;

    // Optimistic update - update local state immediately
    for (const idx of indices) {
      const txn = transactions[idx];
      if (!txn) continue;
      const currentTags = txn.tags || [];
      if (currentTags.includes(tag)) continue;

      // Update in place
      transactions[idx] = {
        ...txn,
        tags: [...currentTags, tag]
      };
    }

    // Force reactivity
    transactions = [...transactions];

    // Move cursor to next untagged if in untagged mode, otherwise just next
    const nextIndex = cursorIndex + 1;
    if (nextIndex < transactions.length) {
      cursorIndex = nextIndex;
      scrollToCursor();
    }

    deselectAll();

    // Persist in background (fire and forget)
    persistTagChanges(indices.map(i => transactions[i]));
  }

  async function persistTagChanges(txns: Transaction[]) {
    try {
      for (const txn of txns) {
        const tagsJson = JSON.stringify(txn.tags);
        const escapedId = txn.transaction_id.replace(/'/g, "''");
        await executeQuery(
          `UPDATE sys_transactions SET tags = '${tagsJson}' WHERE transaction_id = '${escapedId}'`,
          { readonly: false }
        );
      }
    } catch (e) {
      console.error("Failed to persist tags:", e);
      // Could show a toast/notification here
      error = "Failed to save - changes may be lost";
    }
  }

  function startCustomTagging() {
    if (transactions.length === 0) return;
    isCustomTagging = true;
    // Pre-populate with existing tags
    const txn = transactions[cursorIndex];
    if (txn && txn.tags.length > 0) {
      customTagInput = txn.tags.join(", ");
    } else {
      customTagInput = "";
    }
    setTimeout(() => customTagInputEl?.focus(), 10);
  }

  function cancelCustomTagging() {
    isCustomTagging = false;
    customTagInput = "";
    containerEl?.focus();
  }

  async function applyCustomTag() {
    const tags = customTagInput.split(",").map(t => t.trim()).filter(t => t);
    if (tags.length === 0) {
      cancelCustomTagging();
      return;
    }

    const indices = getSelectedIndicesArray();

    // Optimistic update
    for (const idx of indices) {
      const txn = transactions[idx];
      if (!txn) continue;

      // Merge tags (dedupe)
      const currentTags = txn.tags || [];
      const mergedTags = [...new Set([...currentTags, ...tags])];

      transactions[idx] = {
        ...txn,
        tags: mergedTags
      };
    }

    transactions = [...transactions];

    // Move to next
    const nextIndex = cursorIndex + 1;
    if (nextIndex < transactions.length) {
      cursorIndex = nextIndex;
      scrollToCursor();
    }

    deselectAll();
    cancelCustomTagging();

    // Persist in background
    persistTagChanges(indices.map(i => transactions[i]));
  }

  function startBulkTagging() {
    if (transactions.length === 0) return;
    isBulkTagging = true;
    bulkTagInput = "";
    setTimeout(() => bulkTagInputEl?.focus(), 10);
  }

  function cancelBulkTagging() {
    isBulkTagging = false;
    bulkTagInput = "";
    containerEl?.focus();
  }

  async function applyBulkTag() {
    const tags = bulkTagInput.split(",").map(t => t.trim()).filter(t => t);
    if (tags.length === 0) {
      cancelBulkTagging();
      return;
    }

    // Apply to ALL visible transactions
    for (let i = 0; i < transactions.length; i++) {
      const txn = transactions[i];
      const currentTags = txn.tags || [];
      const mergedTags = [...new Set([...currentTags, ...tags])];

      transactions[i] = {
        ...txn,
        tags: mergedTags
      };
    }

    transactions = [...transactions];
    cancelBulkTagging();

    // Persist all in background
    persistTagChanges(transactions);
  }

  // Clear all tags (set to empty)
  async function clearTagsFromCurrent() {
    const indices = getSelectedIndicesArray();
    if (indices.length === 0) return;

    // Optimistic update
    for (const idx of indices) {
      const txn = transactions[idx];
      if (!txn || txn.tags.length === 0) continue;

      transactions[idx] = {
        ...txn,
        tags: []
      };
    }

    transactions = [...transactions];

    // Move to next
    const nextIndex = cursorIndex + 1;
    if (nextIndex < transactions.length) {
      cursorIndex = nextIndex;
      scrollToCursor();
    }

    deselectAll();

    // Persist in background
    persistTagChanges(indices.map(i => transactions[i]));
  }

  // Remove tags (same as clear for now)
  async function removeTagsFromCurrent() {
    await clearTagsFromCurrent();
  }

  function formatAmount(amount: number): string {
    return Math.abs(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  onMount(async () => {
    // Preload tag data in parallel with loading transactions
    await suggester.loadTagData();
    allTags = suggester.getAllTags();
    await loadTransactions();
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
          <span class="mode untagged-mode">Untagged</span>
        {:else}
          <span class="mode">All</span>
        {/if}
      </div>
    </div>
    <div class="stats">
      <span>{transactions.length} transactions</span>
      <span class="tagged-count">| {taggedCount} tagged</span>
      {#if selectedIndices.size > 0}
        <span class="selected-count">| {selectedIndices.size} selected</span>
      {/if}
    </div>
  </div>

  <!-- Help bar -->
  <div class="help-bar">
    <span><kbd>j</kbd><kbd>k</kbd> nav</span>
    <span><kbd>1-9</kbd> quick tag</span>
    <span><kbd>t</kbd> edit tags</span>
    <span><kbd>c</kbd> clear</span>
    <span><kbd>a</kbd> bulk tag</span>
    <span><kbd>/</kbd> search</span>
    <span><kbd>u</kbd> filter</span>
    <span><kbd>r</kbd> reset</span>
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
            onclick={() => handleRowClick(index)}
            role="button"
            tabindex="-1"
          >
            <div class="row-date">{txn.transaction_date}</div>
            <div class="row-account">{txn.account_name || ''}</div>
            <div class="row-desc">{txn.description}</div>
            <div class="row-amount" class:negative={txn.amount < 0} class:positive={txn.amount >= 0}>
              {txn.amount < 0 ? '-' : ''}${formatAmount(txn.amount)}
            </div>
            <div class="row-tags">
              {#if txn.tags.length === 0}
                <span class="no-tags">--</span>
              {:else}
                {#each txn.tags.slice(0, 3) as tag}
                  <span class="tag">{tag}</span>
                {/each}
                {#if txn.tags.length > 3}
                  <span class="tag-more">+{txn.tags.length - 3}</span>
                {/if}
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
  <div class="command-bar" class:active={isSearching || isCustomTagging || isBulkTagging}>
    {#if isSearching}
      <div class="command-input-row">
        <span class="command-prefix">/</span>
        <input
          bind:this={searchInputEl}
          type="text"
          class="command-input"
          bind:value={searchQuery}
          oninput={handleSearchInput}
          onkeydown={handleSearchKeyDown}
          placeholder="type to search (Enter for instant)"
        />
        <span class="command-hint">Enter to search, Esc to exit</span>
      </div>
    {:else if isCustomTagging}
      <div class="command-input-row">
        <span class="command-prefix">tags ({getTargetCount()}):</span>
        <div class="input-with-autocomplete">
          <input
            bind:this={customTagInputEl}
            type="text"
            class="command-input"
            bind:value={customTagInput}
            placeholder="enter tags (comma-separated)"
          />
          {#if tagAutocomplete}
            <span class="autocomplete-ghost">{customTagInput}<span class="autocomplete-hint">{tagAutocomplete}</span></span>
          {/if}
        </div>
        <span class="command-hint">Tab to complete, Enter to apply</span>
      </div>
    {:else if isBulkTagging}
      <div class="command-input-row">
        <span class="command-prefix">bulk tag ({transactions.length}):</span>
        <input
          bind:this={bulkTagInputEl}
          type="text"
          class="command-input"
          bind:value={bulkTagInput}
          placeholder="apply to ALL visible transactions"
        />
        <span class="command-hint">Enter to apply, Esc to cancel</span>
      </div>
    {:else}
      <div class="command-hint-row">
        <kbd>1-9</kbd> quick tag | <kbd>t</kbd> edit | <kbd>c</kbd> clear | <kbd>a</kbd> bulk | <kbd>/</kbd> search | <kbd>u</kbd> filter
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

  .mode.untagged-mode {
    background: var(--accent-danger, #ef4444);
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

  .tagged-count {
    color: var(--text-muted);
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
    cursor: pointer;
  }

  .row:hover {
    background: var(--bg-secondary);
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

  .row-date {
    width: 90px;
    flex-shrink: 0;
    color: var(--text-muted);
    font-size: 12px;
  }

  .row-account {
    width: 100px;
    flex-shrink: 0;
    color: var(--text-muted);
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
  }

  .row-amount.positive {
    color: var(--accent-success, #22c55e);
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

  .tag-more {
    padding: 1px 6px;
    background: var(--bg-tertiary);
    color: var(--text-muted);
    border-radius: 3px;
    font-size: 10px;
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

  .input-with-autocomplete {
    flex: 1;
    position: relative;
  }

  .input-with-autocomplete .command-input {
    position: relative;
    z-index: 1;
    background: transparent;
    width: 100%;
  }

  .autocomplete-ghost {
    position: absolute;
    top: 0;
    left: 0;
    font-family: var(--font-mono);
    font-size: 13px;
    pointer-events: none;
    color: transparent;
    white-space: pre;
  }

  .autocomplete-hint {
    color: var(--text-muted);
    opacity: 0.6;
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
