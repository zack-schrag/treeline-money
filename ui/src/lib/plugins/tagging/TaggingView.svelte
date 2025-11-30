<script lang="ts">
  import { onMount } from "svelte";
  import { executeQuery } from "../../sdk";
  import { FrequencyBasedSuggester, type TagSuggestion, type Transaction } from "./suggestions";

  // Initialize suggester
  const suggester = new FrequencyBasedSuggester();

  let transactions = $state<Transaction[]>([]);
  let suggestions = $state<Map<string, TagSuggestion[]>>(new Map());
  let isLoading = $state(true);
  let isLoadingMore = $state(false);
  let error = $state<string | null>(null);
  let hasMore = $state(true);
  const PAGE_SIZE = 200;

  // Selection state
  let selectedIndices = $state<Set<number>>(new Set());
  let cursorIndex = $state(0);

  // Filter state - default to "all"
  let filterMode = $state<"all" | "untagged">("all");
  let searchQuery = $state("");
  let isSearching = $state(false);
  let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  // Account filter state (multi-select)
  const ACCOUNT_FILTER_KEY = "tagging-selected-accounts";
  let selectedAccounts = $state<Set<string>>(new Set());
  let availableAccounts = $state<string[]>([]);
  let accountsWithIds = $state<{ id: string; name: string }[]>([]);
  let isAccountDropdownOpen = $state(false);
  let accountCursorIndex = $state(0);

  function loadPersistedAccounts(): Set<string> {
    try {
      const stored = localStorage.getItem(ACCOUNT_FILTER_KEY);
      if (stored) {
        const accounts = JSON.parse(stored) as string[];
        return new Set(accounts);
      }
    } catch (e) {
      console.error("Failed to load persisted accounts:", e);
    }
    return new Set();
  }

  function persistSelectedAccounts() {
    try {
      const accounts = Array.from(selectedAccounts);
      localStorage.setItem(ACCOUNT_FILTER_KEY, JSON.stringify(accounts));
    } catch (e) {
      console.error("Failed to persist accounts:", e);
    }
  }

  // Custom tag input mode (for typing a new tag)
  let isCustomTagging = $state(false);
  let customTagInput = $state("");

  // Bulk tag mode
  let isBulkTagging = $state(false);
  let bulkTagInput = $state("");

  // Transaction edit modal
  let isTagModalOpen = $state(false);
  let editingTransaction = $state<Transaction | null>(null);
  let modalTagInput = $state("");
  let modalDescInput = $state("");
  let modalAmountInput = $state("");
  let modalDateInput = $state("");
  let modalInputEl: HTMLInputElement | null = null;

  // Delete confirmation
  let showDeleteConfirm = $state(false);

  // Split modal
  let showSplitModal = $state(false);
  let splitAmounts = $state<{ description: string; amount: string }[]>([
    { description: "", amount: "" },
    { description: "", amount: "" },
  ]);

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

  // Group split transactions by parent_id for visual grouping
  let splitGroups = $derived.by(() => {
    const groups = new Map<string, number[]>();
    transactions.forEach((txn, idx) => {
      if (txn.parent_transaction_id) {
        const existing = groups.get(txn.parent_transaction_id) || [];
        existing.push(idx);
        groups.set(txn.parent_transaction_id, existing);
      }
    });
    return groups;
  });

  // Helper to check if a transaction is part of a split group
  function getSplitGroupInfo(txn: Transaction, index: number): { isFirst: boolean; isLast: boolean; siblingCount: number } | null {
    if (!txn.parent_transaction_id) return null;
    const group = splitGroups.get(txn.parent_transaction_id);
    if (!group || group.length < 2) return null;
    const posInGroup = group.indexOf(index);
    return {
      isFirst: posInGroup === 0,
      isLast: posInGroup === group.length - 1,
      siblingCount: group.length
    };
  }

  // Stats for visible transactions
  let visibleTaggedCount = $derived(transactions.filter(t => t.tags.length > 0).length);

  // Global stats (all transactions in database)
  let globalStats = $state({ total: 0, tagged: 0 });
  let globalUntaggedCount = $derived(globalStats.total - globalStats.tagged);
  let progressPercent = $derived(globalStats.total > 0 ? Math.floor((globalStats.tagged / globalStats.total) * 100) : 0);
  let isAllTagged = $derived(globalStats.total > 0 && globalStats.tagged === globalStats.total);

  // Celebration state
  let showCelebration = $state(false);
  let prevIsAllTagged = false;

  // Watch for 100% completion (all transactions tagged)
  $effect(() => {
    if (isAllTagged && !prevIsAllTagged && !isLoading) {
      triggerCelebration();
    }
    prevIsAllTagged = isAllTagged;
  });

  function triggerCelebration() {
    showCelebration = true;
    setTimeout(() => {
      showCelebration = false;
    }, 3000);
  }

  async function loadGlobalStats() {
    try {
      const result = await executeQuery(`
        SELECT
          COUNT(*) as total,
          COUNT(*) FILTER (WHERE len(tags) > 0) as tagged
        FROM transactions
      `);
      if (result.rows.length > 0) {
        globalStats = {
          total: result.rows[0][0] as number,
          tagged: result.rows[0][1] as number
        };
      }
    } catch (e) {
      console.error("Failed to load global stats:", e);
    }
  }

  async function loadAvailableAccounts() {
    try {
      // Load account names for filtering (from transactions view)
      const result = await executeQuery(`
        SELECT DISTINCT account_name
        FROM transactions
        WHERE account_name IS NOT NULL AND account_name != ''
        ORDER BY account_name
      `);
      availableAccounts = result.rows.map(r => r[0] as string);

      // Load all accounts with IDs for the add transaction modal
      const accountsResult = await executeQuery(`
        SELECT account_id, name
        FROM sys_accounts
        WHERE name IS NOT NULL AND name != ''
        ORDER BY name
      `);
      accountsWithIds = accountsResult.rows.map(r => ({
        id: r[0] as string,
        name: r[1] as string,
      }));
    } catch (e) {
      console.error("Failed to load accounts:", e);
    }
  }

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

  function buildQuery(offset: number = 0): string {
    let query = `
      SELECT
        transaction_id,
        account_id,
        transaction_date,
        description,
        amount,
        tags,
        account_name,
        parent_transaction_id
      FROM transactions
    `;

    const conditions: string[] = [];

    // Account filter (multi-select)
    if (selectedAccounts.size > 0) {
      const accountList = Array.from(selectedAccounts)
        .map(a => `'${a.replace(/'/g, "''")}'`)
        .join(", ");
      conditions.push(`account_name IN (${accountList})`);
    }

    // Untagged filter
    if (filterMode === "untagged" && !searchQuery.trim()) {
      conditions.push("tags = []");
    }

    // Search filter
    if (searchQuery.trim()) {
      const escapedSearch = searchQuery.trim().replace(/'/g, "''");
      // Search across description, account_name, amount (as string), and tags
      conditions.push(`(
        description ILIKE '%${escapedSearch}%'
        OR account_name ILIKE '%${escapedSearch}%'
        OR CAST(amount AS VARCHAR) LIKE '%${escapedSearch}%'
        OR array_to_string(tags, ',') ILIKE '%${escapedSearch}%'
      )`);
    }

    if (conditions.length > 0) {
      query += " WHERE " + conditions.join(" AND ");
    }

    query += ` ORDER BY transaction_date DESC LIMIT ${PAGE_SIZE + 1} OFFSET ${offset}`;
    return query;
  }

  function parseRows(rows: unknown[][]): Transaction[] {
    return rows.map(row => ({
      transaction_id: row[0] as string,
      account_id: row[1] as string,
      transaction_date: row[2] as string,
      description: row[3] as string,
      amount: row[4] as number,
      tags: (row[5] as string[]) || [],
      account_name: row[6] as string,
      parent_transaction_id: row[7] as string | null,
    }));
  }

  async function loadTransactions() {
    isLoading = true;
    error = null;
    hasMore = true;

    try {
      const result = await executeQuery(buildQuery(0));
      const rows = parseRows(result.rows);

      // Check if there are more results
      if (rows.length > PAGE_SIZE) {
        transactions = rows.slice(0, PAGE_SIZE);
        hasMore = true;
      } else {
        transactions = rows;
        hasMore = false;
      }

      // Reset cursor
      cursorIndex = 0;

      // Compute suggestions for all loaded transactions
      suggestions = await suggester.suggestBatch(transactions, 9);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load transactions";
      console.error("Failed to load transactions:", e);
    } finally {
      isLoading = false;
    }
  }

  async function loadMoreTransactions() {
    if (!hasMore || isLoadingMore) return;

    isLoadingMore = true;

    try {
      const result = await executeQuery(buildQuery(transactions.length));
      const rows = parseRows(result.rows);

      if (rows.length > PAGE_SIZE) {
        transactions = [...transactions, ...rows.slice(0, PAGE_SIZE)];
        hasMore = true;
      } else {
        transactions = [...transactions, ...rows];
        hasMore = false;
      }

      // Compute suggestions for new transactions
      const newSuggestions = await suggester.suggestBatch(rows.slice(0, PAGE_SIZE), 9);
      suggestions = new Map([...suggestions, ...newSuggestions]);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load more";
      console.error("Failed to load more transactions:", e);
    } finally {
      isLoadingMore = false;
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

    // Account dropdown open - handle navigation
    if (isAccountDropdownOpen) {
      handleAccountFilterKeyDown(e);
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
      case "Enter":
        e.preventDefault();
        if (transactions[cursorIndex]) {
          openTagModal(transactions[cursorIndex]);
        }
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
      case "f":
        e.preventDefault();
        startAccountFiltering();
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
      case "+":
      case "=":
        e.preventDefault();
        openAddModal();
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

  function handleAccountFilterKeyDown(e: KeyboardEvent) {
    switch (e.key) {
      case "Escape":
        e.preventDefault();
        closeAccountDropdown();
        break;
      case "j":
      case "ArrowDown":
        e.preventDefault();
        accountCursorIndex = Math.min(accountCursorIndex + 1, availableAccounts.length - 1);
        scrollAccountCursor();
        break;
      case "k":
      case "ArrowUp":
        e.preventDefault();
        accountCursorIndex = Math.max(accountCursorIndex - 1, 0);
        scrollAccountCursor();
        break;
      case " ":
      case "x":
        e.preventDefault();
        toggleAccountSelection(availableAccounts[accountCursorIndex]);
        break;
      case "Enter":
        e.preventDefault();
        applyAccountFilterAndClose();
        break;
      case "a":
        // Select all
        e.preventDefault();
        selectedAccounts = new Set(availableAccounts);
        break;
      case "A":
        // Deselect all
        e.preventDefault();
        selectedAccounts = new Set();
        break;
    }
  }

  function scrollAccountCursor() {
    setTimeout(() => {
      const element = document.querySelector(`[data-account-index="${accountCursorIndex}"]`);
      if (element) {
        element.scrollIntoView({ block: "nearest", behavior: "auto" });
      }
    }, 0);
  }

  function startAccountFiltering() {
    if (availableAccounts.length === 0) return;
    isAccountDropdownOpen = true;
    accountCursorIndex = 0;
  }

  function closeAccountDropdown() {
    isAccountDropdownOpen = false;
    containerEl?.focus();
  }

  function toggleAccountSelection(account: string) {
    if (!account) return;
    if (selectedAccounts.has(account)) {
      selectedAccounts.delete(account);
    } else {
      selectedAccounts.add(account);
    }
    selectedAccounts = new Set(selectedAccounts); // trigger reactivity
  }

  function applyAccountFilterAndClose() {
    isAccountDropdownOpen = false;
    persistSelectedAccounts();
    loadTransactions();
    containerEl?.focus();
  }

  function clearAccountFilter() {
    selectedAccounts = new Set();
    persistSelectedAccounts();
    loadTransactions();
  }

  function toggleAccountDropdown() {
    if (isAccountDropdownOpen) {
      closeAccountDropdown();
    } else {
      startAccountFiltering();
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
    selectedAccounts = new Set();
    persistSelectedAccounts();
    loadTransactions();
  }

  function moveCursor(delta: number) {
    const newIndex = cursorIndex + delta;
    if (newIndex >= 0 && newIndex < transactions.length) {
      cursorIndex = newIndex;
      scrollToCursor();

      // Auto-load more when near the end (within 20 items)
      if (hasMore && !isLoadingMore && cursorIndex >= transactions.length - 20) {
        loadMoreTransactions();
      }
    }
  }

  function pageUp() {
    cursorIndex = Math.max(0, cursorIndex - 20);
    scrollToCursor();
  }

  function pageDown() {
    cursorIndex = Math.min(transactions.length - 1, cursorIndex + 20);
    scrollToCursor();

    // Auto-load more when near the end
    if (hasMore && !isLoadingMore && cursorIndex >= transactions.length - 20) {
      loadMoreTransactions();
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

  function handleRowClick(index: number) {
    cursorIndex = index;
    containerEl?.focus();
  }

  function handleRowDoubleClick(index: number) {
    const txn = transactions[index];
    if (txn) {
      openTagModal(txn);
    }
  }

  function handleListScroll(e: Event) {
    const target = e.target as HTMLElement;
    const scrollBottom = target.scrollHeight - target.scrollTop - target.clientHeight;

    // Load more when within 100px of the bottom
    if (scrollBottom < 100 && hasMore && !isLoadingMore) {
      loadMoreTransactions();
    }
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

  async function persistTagChanges(txns: Transaction[], tagAdded: boolean = true) {
    try {
      for (const txn of txns) {
        const tagsJson = JSON.stringify(txn.tags);
        const escapedId = txn.transaction_id.replace(/'/g, "''");
        await executeQuery(
          `UPDATE sys_transactions SET tags = '${tagsJson}' WHERE transaction_id = '${escapedId}'`,
          { readonly: false }
        );
      }
      // Refresh global stats after persisting
      await loadGlobalStats();
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

  // Transaction edit modal functions
  function openTagModal(txn: Transaction) {
    editingTransaction = txn;
    modalTagInput = txn.tags.join(", ");
    modalDescInput = txn.description;
    modalAmountInput = txn.amount.toString();
    modalDateInput = txn.transaction_date;
    isTagModalOpen = true;
    setTimeout(() => modalInputEl?.focus(), 10);
  }

  function closeTagModal() {
    isTagModalOpen = false;
    editingTransaction = null;
    modalTagInput = "";
    modalDescInput = "";
    modalAmountInput = "";
    modalDateInput = "";
    containerEl?.focus();
  }

  async function saveTagModal() {
    if (!editingTransaction) return;

    const newTags = modalTagInput.split(",").map(t => t.trim()).filter(t => t);
    const newDesc = modalDescInput.trim();
    const newAmount = parseFloat(modalAmountInput);
    const newDate = modalDateInput.trim();

    // Validate amount
    if (isNaN(newAmount)) {
      error = "Invalid amount";
      return;
    }

    // Validate date format (basic check)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(newDate)) {
      error = "Date must be in YYYY-MM-DD format";
      return;
    }

    // Find the transaction in our list and update it
    const idx = transactions.findIndex(t => t.transaction_id === editingTransaction!.transaction_id);
    if (idx >= 0) {
      transactions[idx] = {
        ...transactions[idx],
        tags: newTags,
        description: newDesc,
        amount: newAmount,
        transaction_date: newDate
      };
      transactions = [...transactions];

      // Persist all changes
      await persistTransactionChanges(transactions[idx]);
    }

    closeTagModal();
  }

  async function persistTransactionChanges(txn: Transaction) {
    try {
      const tagsJson = JSON.stringify(txn.tags);
      const escapedId = txn.transaction_id.replace(/'/g, "''");
      const escapedDesc = txn.description.replace(/'/g, "''");

      await executeQuery(
        `UPDATE sys_transactions SET
          tags = '${tagsJson}',
          description = '${escapedDesc}',
          amount = ${txn.amount},
          transaction_date = '${txn.transaction_date}'
        WHERE transaction_id = '${escapedId}'`,
        { readonly: false }
      );

      // Refresh global stats after persisting
      await loadGlobalStats();
    } catch (e) {
      console.error("Failed to persist transaction:", e);
      error = "Failed to save - changes may be lost";
    }
  }

  function handleModalKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeTagModal();
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      saveTagModal();
    }
  }

  // Delete transaction
  async function deleteTransaction() {
    if (!editingTransaction) return;

    try {
      const now = new Date().toISOString();
      await executeQuery(
        `UPDATE sys_transactions SET deleted_at = '${now}' WHERE transaction_id = '${editingTransaction.transaction_id}'`,
        { readonly: false }
      );

      // Remove from local list
      transactions = transactions.filter(
        (t) => t.transaction_id !== editingTransaction!.transaction_id
      );

      showDeleteConfirm = false;
      closeTagModal();
      await loadGlobalStats();
    } catch (e) {
      console.error("Failed to delete transaction:", e);
      error = e instanceof Error ? e.message : "Failed to delete transaction";
    }
  }

  // Split transaction
  function openSplitModal() {
    if (!editingTransaction) return;
    splitAmounts = [
      { description: editingTransaction.description || "", amount: "" },
      { description: "", amount: "" },
    ];
    showSplitModal = true;
  }

  function closeSplitModal() {
    showSplitModal = false;
    splitAmounts = [
      { description: "", amount: "" },
      { description: "", amount: "" },
    ];
  }

  function addSplitRow() {
    splitAmounts = [...splitAmounts, { description: "", amount: "" }];
  }

  function removeSplitRow(index: number) {
    if (splitAmounts.length > 2) {
      splitAmounts = splitAmounts.filter((_, i) => i !== index);
    }
  }

  function generateUUID(): string {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  async function executeSplit() {
    if (!editingTransaction) return;

    // Validate amounts sum to original
    const originalAmount = editingTransaction.amount;
    const splitTotal = splitAmounts.reduce((sum, s) => {
      const amt = parseFloat(s.amount);
      return sum + (isNaN(amt) ? 0 : amt);
    }, 0);

    // Allow small floating point differences
    if (Math.abs(splitTotal - originalAmount) > 0.01) {
      error = `Split amounts (${splitTotal.toFixed(2)}) must equal original amount (${originalAmount.toFixed(2)})`;
      return;
    }

    try {
      const now = new Date().toISOString();
      const parentId = editingTransaction.transaction_id;

      // Soft-delete the parent transaction
      await executeQuery(
        `UPDATE sys_transactions SET deleted_at = '${now}' WHERE transaction_id = '${parentId}'`,
        { readonly: false }
      );

      // Insert child transactions
      const newTransactions: Transaction[] = [];
      for (const split of splitAmounts) {
        const amt = parseFloat(split.amount);
        if (isNaN(amt) || amt === 0) continue;

        const childId = generateUUID();
        const desc = split.description.replace(/'/g, "''");

        await executeQuery(
          `INSERT INTO sys_transactions (
            transaction_id, account_id, amount, description,
            transaction_date, posted_date, tags, external_ids,
            parent_transaction_id, created_at, updated_at
          ) VALUES (
            '${childId}',
            '${editingTransaction.account_id}',
            ${amt},
            '${desc}',
            '${editingTransaction.transaction_date}',
            '${editingTransaction.transaction_date}',
            ${editingTransaction.tags.length > 0 ? `ARRAY[${editingTransaction.tags.map((t) => `'${t}'`).join(",")}]` : "NULL"},
            '{}',
            '${parentId}',
            '${now}',
            '${now}'
          )`,
          { readonly: false }
        );

        // Add to local list for display
        newTransactions.push({
          transaction_id: childId,
          account_id: editingTransaction.account_id,
          account_name: editingTransaction.account_name,
          amount: amt,
          description: split.description,
          transaction_date: editingTransaction.transaction_date,
          tags: [...editingTransaction.tags],
          parent_transaction_id: parentId,
        });
      }

      // Replace parent with children in local list
      const parentIdx = transactions.findIndex(t => t.transaction_id === parentId);
      if (parentIdx >= 0) {
        transactions.splice(parentIdx, 1, ...newTransactions);
        transactions = [...transactions];
      }

      // Generate suggestions for the new split transactions
      const newSuggestions = await suggester.suggestBatch(newTransactions, 9);
      suggestions = new Map([...suggestions, ...newSuggestions]);

      closeSplitModal();
      closeTagModal();
      await loadGlobalStats();
    } catch (e) {
      console.error("Failed to split transaction:", e);
      error = e instanceof Error ? e.message : "Failed to split transaction";
    }
  }

  // Unsplit confirmation
  let showUnsplitConfirm = $state(false);

  // Add transaction modal
  let showAddModal = $state(false);
  let addDescInput = $state("");
  let addAmountInput = $state("");
  let addDateInput = $state(new Date().toISOString().split("T")[0]);
  let addAccountId = $state("");
  let addTagsInput = $state("");

  async function unsplitTransaction() {
    if (!editingTransaction || !editingTransaction.parent_transaction_id) return;

    const parentId = editingTransaction.parent_transaction_id;

    try {
      const now = new Date().toISOString();

      // Delete all children of this parent (soft delete)
      await executeQuery(
        `UPDATE sys_transactions SET deleted_at = '${now}' WHERE parent_transaction_id = '${parentId}'`,
        { readonly: false }
      );

      // Restore the parent (clear deleted_at)
      await executeQuery(
        `UPDATE sys_transactions SET deleted_at = NULL WHERE transaction_id = '${parentId}'`,
        { readonly: false }
      );

      // Reload transactions to get fresh data
      showUnsplitConfirm = false;
      closeTagModal();
      await loadTransactions();
      await loadGlobalStats();
    } catch (e) {
      console.error("Failed to unsplit transaction:", e);
      error = e instanceof Error ? e.message : "Failed to unsplit transaction";
    }
  }

  // Add transaction functions
  function openAddModal() {
    addDescInput = "";
    addAmountInput = "";
    addDateInput = new Date().toISOString().split("T")[0];
    addAccountId = "";
    addTagsInput = "";
    showAddModal = true;
  }

  function closeAddModal() {
    showAddModal = false;
    containerEl?.focus();
  }

  async function saveNewTransaction() {
    // Validate inputs
    const desc = addDescInput.trim();
    if (!desc) {
      error = "Description is required";
      return;
    }

    const amount = parseFloat(addAmountInput);
    if (isNaN(amount)) {
      error = "Invalid amount";
      return;
    }

    if (!addAccountId) {
      error = "Please select an account";
      return;
    }

    if (!/^\d{4}-\d{2}-\d{2}$/.test(addDateInput)) {
      error = "Date must be in YYYY-MM-DD format";
      return;
    }

    const tags = addTagsInput.split(",").map(t => t.trim()).filter(t => t);

    try {
      const now = new Date().toISOString();
      const txnId = generateUUID();
      const escapedDesc = desc.replace(/'/g, "''");

      // Find account name for the selected account
      const selectedAccount = accountsWithIds.find(a => a.id === addAccountId);
      const accountName = selectedAccount?.name || "";

      await executeQuery(
        `INSERT INTO sys_transactions (
          transaction_id, account_id, amount, description,
          transaction_date, posted_date, tags, external_ids,
          created_at, updated_at
        ) VALUES (
          '${txnId}',
          '${addAccountId}',
          ${amount},
          '${escapedDesc}',
          '${addDateInput}',
          '${addDateInput}',
          ${tags.length > 0 ? `ARRAY[${tags.map((t) => `'${t}'`).join(",")}]` : "NULL"},
          '{"manual": true}',
          '${now}',
          '${now}'
        )`,
        { readonly: false }
      );

      // Add to local list
      const newTxn: Transaction = {
        transaction_id: txnId,
        account_id: addAccountId,
        account_name: accountName,
        amount,
        description: desc,
        transaction_date: addDateInput,
        tags,
        parent_transaction_id: null,
      };

      // Add to front since it's likely recent
      transactions = [newTxn, ...transactions];

      // Generate suggestions for the new transaction
      const newSuggestions = await suggester.suggestBatch([newTxn], 9);
      suggestions = new Map([...suggestions, ...newSuggestions]);

      closeAddModal();
      await loadGlobalStats();
    } catch (e) {
      console.error("Failed to add transaction:", e);
      error = e instanceof Error ? e.message : "Failed to add transaction";
    }
  }

  function formatAmount(amount: number): string {
    return Math.abs(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  onMount(async () => {
    // Load persisted account filter
    selectedAccounts = loadPersistedAccounts();

    // Preload tag data and accounts in parallel with loading transactions
    await suggester.loadTagData();
    allTags = suggester.getAllTags();
    await Promise.all([loadGlobalStats(), loadAvailableAccounts()]);

    // Filter out any persisted accounts that no longer exist
    if (selectedAccounts.size > 0) {
      const validAccounts = new Set(
        Array.from(selectedAccounts).filter(a => availableAccounts.includes(a))
      );
      if (validAccounts.size !== selectedAccounts.size) {
        selectedAccounts = validAccounts;
        persistSelectedAccounts();
      }
    }

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
  <!-- Confetti celebration -->
  {#if showCelebration}
    <div class="confetti-container">
      {#each Array(50) as _, i}
        <div class="confetti" style="--delay: {Math.random() * 3}s; --x: {Math.random() * 100}vw; --rotation: {Math.random() * 360}deg; --color: {['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'][i % 6]}"></div>
      {/each}
    </div>
  {/if}

  <!-- Header -->
  <div class="header">
    <div class="title-row">
      <h1 class="title">Transactions</h1>

      <button class="add-btn" onclick={openAddModal} title="Add transaction (+)">
        + Add
      </button>

      <!-- Progress Ring -->
      {#if globalStats.total > 0}
        <div class="progress-ring-container" class:complete={isAllTagged}>
          <svg class="progress-ring" viewBox="0 0 36 36">
            <path
              class="progress-ring-bg"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              class="progress-ring-fill"
              stroke-dasharray="{progressPercent}, 100"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <span class="progress-text">{progressPercent}%</span>
        </div>
      {/if}

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

      <!-- Account filter dropdown -->
      <div class="account-filter-container">
        <button
          class="account-filter-btn"
          class:active={selectedAccounts.size > 0}
          onclick={toggleAccountDropdown}
        >
          {#if selectedAccounts.size === 0}
            All Accounts
          {:else if selectedAccounts.size === 1}
            {Array.from(selectedAccounts)[0]}
          {:else}
            {selectedAccounts.size} accounts
          {/if}
          <span class="dropdown-arrow">{isAccountDropdownOpen ? "▲" : "▼"}</span>
        </button>

        {#if isAccountDropdownOpen}
          <div class="account-dropdown">
            <div class="dropdown-header">
              <span class="dropdown-title">Filter by Account</span>
              {#if selectedAccounts.size > 0}
                <button class="clear-selection" onclick={clearAccountFilter}>Clear</button>
              {/if}
            </div>
            <div class="dropdown-hint">
              <kbd>j</kbd><kbd>k</kbd> navigate | <kbd>space</kbd> toggle | <kbd>Enter</kbd> apply
            </div>
            <div class="account-list">
              {#each availableAccounts as account, i}
                <button
                  class="account-option"
                  class:cursor={accountCursorIndex === i}
                  class:selected={selectedAccounts.has(account)}
                  data-account-index={i}
                  onclick={() => toggleAccountSelection(account)}
                >
                  <span class="checkbox">{selectedAccounts.has(account) ? "☑" : "☐"}</span>
                  <span class="account-name">{account}</span>
                </button>
              {/each}
            </div>
            <div class="dropdown-footer">
              <button class="dropdown-apply" onclick={applyAccountFilterAndClose}>
                Apply Filter
              </button>
            </div>
          </div>
        {/if}
      </div>
    </div>
    <div class="stats">
      <span>Viewing {transactions.length}{hasMore ? '+' : ''}</span>
      <span class="tagged-count">| {globalStats.tagged}/{globalStats.total} tagged</span>
      {#if globalUntaggedCount > 0}
        <span class="untagged-count">| {globalUntaggedCount} left</span>
      {/if}
      {#if selectedIndices.size > 0}
        <span class="selected-count">| {selectedIndices.size} selected</span>
      {/if}
      {#if isLoadingMore}
        <span class="loading-more">| loading...</span>
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
    <span><kbd>+</kbd> add</span>
    <span><kbd>/</kbd> search</span>
    <span><kbd>f</kbd> account</span>
    <span><kbd>u</kbd> untagged</span>
    <span><kbd>n</kbd> next</span>
  </div>

  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  <!-- Main content area: list + sidebar -->
  <div class="main-content">
    <!-- Transaction list -->
    <div class="list-container" onscroll={handleListScroll}>
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
          {@const splitInfo = getSplitGroupInfo(txn, index)}
          <div
            class="row"
            class:cursor={cursorIndex === index}
            class:selected={selectedIndices.has(index)}
            class:split-child={!!txn.parent_transaction_id}
            class:split-first={splitInfo?.isFirst}
            class:split-last={splitInfo?.isLast}
            data-index={index}
            onclick={() => handleRowClick(index)}
            ondblclick={() => handleRowDoubleClick(index)}
            role="button"
            tabindex="-1"
          >
            {#if txn.parent_transaction_id}
              <div class="split-indicator" title="Split transaction">
                <span class="split-line"></span>
              </div>
            {/if}
            <div class="row-date">{txn.transaction_date}</div>
            <div class="row-account">{txn.account_name || ''}</div>
            <div class="row-desc">
              {#if txn.parent_transaction_id}
                <span class="split-badge" title="Part of split">⑂</span>
              {/if}
              {txn.description}
            </div>
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
            <button
              class="row-edit-btn"
              onclick={(e) => { e.stopPropagation(); openTagModal(txn); }}
              title="Edit transaction"
            >⋮</button>
          </div>
        {/each}
        {#if isLoadingMore}
          <div class="loading-spinner">
            <span class="spinner"></span>
            <span>Loading more...</span>
          </div>
        {:else if hasMore}
          <div class="load-more-hint">Scroll for more</div>
        {/if}
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

      {#if currentTxn?.parent_transaction_id}
        {@const siblingIndices = splitGroups.get(currentTxn.parent_transaction_id) || []}
        {@const siblings = siblingIndices.map(i => transactions[i]).filter(Boolean)}
        <div class="sidebar-section split-info">
          <div class="sidebar-title">Split Transaction</div>
          <div class="split-siblings">
            {#each siblings as sibling}
              <div class="split-sibling" class:current={sibling.transaction_id === currentTxn.transaction_id}>
                <span class="sibling-desc">{sibling.description}</span>
                <span class="sibling-amount" class:negative={sibling.amount < 0}>
                  ${Math.abs(sibling.amount).toFixed(2)}
                </span>
              </div>
            {/each}
            <div class="split-total">
              <span class="total-label">Total:</span>
              <span class="total-amount">${Math.abs(siblings.reduce((sum, s) => sum + s.amount, 0)).toFixed(2)}</span>
            </div>
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
        <span class="input-wrapper">
          <input
            bind:this={customTagInputEl}
            type="text"
            class="command-input"
            bind:value={customTagInput}
            placeholder="enter tags (comma-separated)"
          />{#if tagAutocomplete}<span class="autocomplete-hint" style="left: {customTagInput.length}ch">{tagAutocomplete}</span>{/if}
        </span>
        <span class="command-hint">Tab to complete</span>
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
        <kbd>1-9</kbd> quick tag | <kbd>Enter</kbd> edit | <kbd>c</kbd> clear | <kbd>a</kbd> bulk | <kbd>/</kbd> search | <kbd>u</kbd> filter
      </div>
    {/if}
  </div>
</div>

<!-- Tag Edit Modal -->
{#if isTagModalOpen && editingTransaction}
  <div
    class="modal-overlay"
    onclick={closeTagModal}
    onkeydown={handleModalKeyDown}
    role="dialog"
    tabindex="-1"
  >
    <div class="modal" onclick={(e) => e.stopPropagation()} role="document">
      <div class="modal-header">
        <span class="modal-title">Edit Transaction</span>
        <button class="close-btn" onclick={closeTagModal}>×</button>
      </div>

      <div class="modal-body">
        {#if editingTransaction.parent_transaction_id}
          <div class="split-notice">
            <span class="split-badge">⑂</span> Part of a split transaction
          </div>
        {/if}

        <div class="form-row">
          <div class="form-group flex-2">
            <label for="modal-desc">Description</label>
            <input
              id="modal-desc"
              type="text"
              bind:this={modalInputEl}
              bind:value={modalDescInput}
              placeholder="Transaction description"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="modal-date">Date</label>
            <input
              id="modal-date"
              type="date"
              bind:value={modalDateInput}
            />
          </div>
          <div class="form-group">
            <label for="modal-amount">Amount</label>
            <input
              id="modal-amount"
              type="text"
              bind:value={modalAmountInput}
              placeholder="0.00"
              class="amount-input"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="modal-tags">Tags (comma-separated)</label>
          <input
            id="modal-tags"
            type="text"
            bind:value={modalTagInput}
            onkeydown={handleModalKeyDown}
            placeholder="e.g., groceries, food, weekly"
          />
        </div>

        {#if currentSuggestions.length > 0}
          <div class="suggested-tags">
            <span class="suggested-label">Suggested:</span>
            {#each currentSuggestions.slice(0, 5) as suggestion}
              <button
                class="suggested-tag-btn"
                onclick={() => {
                  const current = modalTagInput.trim();
                  modalTagInput = current ? `${current}, ${suggestion.tag}` : suggestion.tag;
                }}
              >
                {suggestion.tag}
              </button>
            {/each}
          </div>
        {/if}

        <div class="account-info">
          <span class="account-label">Account:</span>
          <span class="account-value">{editingTransaction.account_name || 'Unknown'}</span>
        </div>
      </div>

      <div class="modal-actions">
        <button class="btn danger" onclick={() => showDeleteConfirm = true}>Delete</button>
        {#if editingTransaction.parent_transaction_id}
          <button class="btn secondary" onclick={() => showUnsplitConfirm = true}>Unsplit</button>
        {:else}
          <button class="btn secondary" onclick={openSplitModal}>Split</button>
        {/if}
        <div class="modal-actions-spacer"></div>
        <button class="btn secondary" onclick={closeTagModal}>Cancel</button>
        <button class="btn primary" onclick={saveTagModal}>Save</button>
      </div>
    </div>
  </div>
{/if}

<!-- Unsplit Confirmation Modal -->
{#if showUnsplitConfirm && editingTransaction}
  <div
    class="modal-overlay confirm-overlay"
    onclick={() => showUnsplitConfirm = false}
    onkeydown={(e) => e.key === "Escape" && (showUnsplitConfirm = false)}
    role="dialog"
    tabindex="-1"
  >
    <div class="modal confirm-modal" onclick={(e) => e.stopPropagation()} role="document">
      <div class="modal-header">
        <span class="modal-title">Unsplit Transaction?</span>
      </div>
      <div class="modal-body">
        <p>This will restore the original transaction and remove all split parts.</p>
        <p class="confirm-note">The original transaction will be restored with its original amount.</p>
      </div>
      <div class="modal-actions">
        <button class="btn secondary" onclick={() => showUnsplitConfirm = false}>Cancel</button>
        <button class="btn primary" onclick={unsplitTransaction}>Unsplit</button>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteConfirm && editingTransaction}
  <div
    class="modal-overlay confirm-overlay"
    onclick={() => showDeleteConfirm = false}
    onkeydown={(e) => e.key === "Escape" && (showDeleteConfirm = false)}
    role="dialog"
    tabindex="-1"
  >
    <div class="modal confirm-modal" onclick={(e) => e.stopPropagation()} role="document">
      <div class="modal-header">
        <span class="modal-title">Delete Transaction?</span>
      </div>
      <div class="modal-body">
        <p>Are you sure you want to delete this transaction?</p>
        <div class="txn-preview">
          <div class="txn-preview-desc">{editingTransaction.description}</div>
          <div class="txn-preview-amount" class:negative={editingTransaction.amount < 0}>
            {editingTransaction.amount < 0 ? '-' : ''}${formatAmount(editingTransaction.amount)}
          </div>
        </div>
        <p class="confirm-note">This transaction won't be re-imported during sync.</p>
      </div>
      <div class="modal-actions">
        <button class="btn secondary" onclick={() => showDeleteConfirm = false}>Cancel</button>
        <button class="btn danger" onclick={deleteTransaction}>Delete</button>
      </div>
    </div>
  </div>
{/if}

<!-- Split Transaction Modal -->
{#if showSplitModal && editingTransaction}
  <div
    class="modal-overlay"
    onclick={closeSplitModal}
    onkeydown={(e) => e.key === "Escape" && closeSplitModal()}
    role="dialog"
    tabindex="-1"
  >
    <div class="modal split-modal" onclick={(e) => e.stopPropagation()} role="document">
      <div class="modal-header">
        <span class="modal-title">Split Transaction</span>
        <button class="close-btn" onclick={closeSplitModal}>×</button>
      </div>
      <div class="modal-body">
        <div class="txn-preview">
          <div class="txn-preview-desc">{editingTransaction.description}</div>
          <div class="txn-preview-amount" class:negative={editingTransaction.amount < 0}>
            Original: {editingTransaction.amount < 0 ? '-' : ''}${formatAmount(editingTransaction.amount)}
          </div>
        </div>

        <div class="split-rows">
          {#each splitAmounts as split, i}
            <div class="split-row">
              <input
                type="text"
                class="split-desc"
                bind:value={split.description}
                placeholder="Description"
              />
              <input
                type="text"
                class="split-amount"
                bind:value={split.amount}
                placeholder="0.00"
              />
              {#if splitAmounts.length > 2}
                <button class="btn-icon" onclick={() => removeSplitRow(i)}>×</button>
              {/if}
            </div>
          {/each}
        </div>

        <button class="btn secondary add-split-btn" onclick={addSplitRow}>+ Add Row</button>

        {#if true}
          {@const splitTotal = splitAmounts.reduce((sum, s) => sum + (parseFloat(s.amount) || 0), 0)}
          {@const remaining = editingTransaction.amount - splitTotal}
          <div class="split-summary" class:error={Math.abs(remaining) > 0.01}>
            Total: ${splitTotal.toFixed(2)} | Remaining: ${remaining.toFixed(2)}
          </div>
        {/if}
      </div>
      <div class="modal-actions">
        <button class="btn secondary" onclick={closeSplitModal}>Cancel</button>
        <button
          class="btn primary"
          onclick={executeSplit}
          disabled={Math.abs(editingTransaction.amount - splitAmounts.reduce((sum, s) => sum + (parseFloat(s.amount) || 0), 0)) > 0.01}
        >
          Split
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Add Transaction Modal -->
{#if showAddModal}
  <div
    class="modal-overlay"
    onclick={closeAddModal}
    onkeydown={(e) => e.key === "Escape" && closeAddModal()}
    role="dialog"
    tabindex="-1"
  >
    <div class="modal" onclick={(e) => e.stopPropagation()} role="document">
      <div class="modal-header">
        <span class="modal-title">Add Transaction</span>
        <button class="close-btn" onclick={closeAddModal}>×</button>
      </div>

      <div class="modal-body">
        <div class="form-row">
          <div class="form-group flex-2">
            <label for="add-desc">Description</label>
            <input
              id="add-desc"
              type="text"
              bind:value={addDescInput}
              placeholder="Transaction description"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="add-date">Date</label>
            <input
              id="add-date"
              type="date"
              bind:value={addDateInput}
            />
          </div>
          <div class="form-group">
            <label for="add-amount">Amount</label>
            <input
              id="add-amount"
              type="text"
              bind:value={addAmountInput}
              placeholder="0.00 (negative for expense)"
              class="amount-input"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="add-account">Account</label>
          <select id="add-account" bind:value={addAccountId} class="account-select">
            <option value="">Select an account...</option>
            {#each accountsWithIds as account}
              <option value={account.id}>{account.name}</option>
            {/each}
          </select>
        </div>

        <div class="form-group">
          <label for="add-tags">Tags (comma-separated)</label>
          <input
            id="add-tags"
            type="text"
            bind:value={addTagsInput}
            placeholder="e.g., groceries, food"
          />
        </div>
      </div>

      <div class="modal-actions">
        <button class="btn secondary" onclick={closeAddModal}>Cancel</button>
        <button class="btn primary" onclick={saveNewTransaction}>Add Transaction</button>
      </div>
    </div>
  </div>
{/if}

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

  .add-btn {
    padding: 4px 12px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border: none;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .add-btn:hover {
    opacity: 0.9;
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

  /* Account filter dropdown */
  .account-filter-container {
    position: relative;
    margin-left: auto;
  }

  .account-filter-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: 4px 10px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 12px;
    cursor: pointer;
    min-width: 140px;
    justify-content: space-between;
  }

  .account-filter-btn:hover {
    border-color: var(--accent-primary);
  }

  .account-filter-btn.active {
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-color: var(--accent-primary);
  }

  .dropdown-arrow {
    font-size: 8px;
    opacity: 0.7;
  }

  .account-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 4px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 100;
    min-width: 250px;
    display: flex;
    flex-direction: column;
  }

  .dropdown-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-primary);
  }

  .dropdown-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .clear-selection {
    background: none;
    border: none;
    color: var(--accent-primary);
    font-size: 11px;
    cursor: pointer;
    padding: 2px 6px;
  }

  .clear-selection:hover {
    text-decoration: underline;
  }

  .dropdown-hint {
    padding: 6px 12px;
    font-size: 10px;
    color: var(--text-muted);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-primary);
  }

  .dropdown-hint kbd {
    display: inline-block;
    padding: 1px 3px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 2px;
    font-family: var(--font-mono);
    font-size: 9px;
    margin-right: 2px;
  }

  .account-list {
    max-height: 300px;
    overflow-y: auto;
  }

  .account-option {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 12px;
    cursor: pointer;
    text-align: left;
  }

  .account-option:hover {
    background: var(--bg-tertiary);
  }

  .account-option.cursor {
    background: var(--bg-tertiary);
    border-left: 3px solid var(--accent-primary);
    padding-left: 9px;
  }

  .account-option.selected {
    font-weight: 600;
  }

  .account-option.selected .checkbox {
    color: var(--accent-primary);
  }

  .checkbox {
    font-size: 14px;
    width: 18px;
    text-align: center;
    flex-shrink: 0;
  }

  .account-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dropdown-footer {
    padding: 8px 12px;
    border-top: 1px solid var(--border-primary);
  }

  .dropdown-apply {
    width: 100%;
    padding: 6px 12px;
    background: var(--accent-primary);
    color: var(--bg-primary);
    border: none;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .dropdown-apply:hover {
    opacity: 0.9;
  }

  .stats {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .loading-more {
    color: var(--accent-primary);
    font-style: italic;
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

  .split-info {
    border-top: 1px solid var(--border-primary);
    padding-top: var(--spacing-md);
  }

  .split-siblings {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 11px;
  }

  .split-sibling {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 6px;
    background: var(--bg-primary);
    border-radius: 3px;
    gap: 8px;
  }

  .split-sibling.current {
    background: var(--bg-tertiary);
    border-left: 2px solid var(--accent-primary);
    padding-left: 4px;
  }

  .sibling-desc {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-muted);
  }

  .split-sibling.current .sibling-desc {
    color: var(--text-primary);
  }

  .sibling-amount {
    flex-shrink: 0;
    font-family: var(--font-mono);
    color: var(--text-primary);
  }

  .sibling-amount.negative {
    color: var(--accent-danger);
  }

  .split-total {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 6px;
    border-top: 1px solid var(--border-primary);
    margin-top: 4px;
  }

  .total-label {
    color: var(--text-muted);
    font-weight: 500;
  }

  .total-amount {
    font-family: var(--font-mono);
    font-weight: 600;
    color: var(--text-primary);
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

  .row-edit-btn {
    width: 24px;
    height: 24px;
    padding: 0;
    background: transparent;
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-muted);
    font-size: 12px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s;
    flex-shrink: 0;
  }

  .row:hover .row-edit-btn,
  .row.cursor .row-edit-btn {
    opacity: 1;
  }

  /* Split transaction styles */
  .row.split-child {
    position: relative;
    padding-left: calc(var(--spacing-lg) + 12px);
  }

  .row.split-child.cursor {
    padding-left: calc(var(--spacing-lg) + 12px - 3px);
  }

  .split-indicator {
    position: absolute;
    left: var(--spacing-lg);
    top: 0;
    bottom: 0;
    width: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .row.split-child.cursor .split-indicator {
    left: calc(var(--spacing-lg) - 3px);
  }

  .split-line {
    width: 2px;
    height: 100%;
    background: var(--text-muted);
    opacity: 0.3;
  }

  .row.split-first .split-line {
    border-radius: 2px 2px 0 0;
    margin-top: 4px;
    height: calc(100% - 4px);
  }

  .row.split-last .split-line {
    border-radius: 0 0 2px 2px;
    margin-bottom: 4px;
    height: calc(100% - 4px);
  }

  .split-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    color: var(--text-muted);
    margin-right: 4px;
    opacity: 0.6;
  }

  .row-edit-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--text-muted);
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

  .input-wrapper {
    flex: 1;
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-wrapper .command-input {
    width: 100%;
    background: transparent;
    padding: 0;
    margin: 0;
    line-height: 1;
  }

  .autocomplete-hint {
    position: absolute;
    top: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    color: var(--text-muted);
    opacity: 0.6;
    font-family: var(--font-mono);
    font-size: 13px;
    pointer-events: none;
    white-space: nowrap;
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

  .loading-spinner {
    padding: 20px;
    text-align: center;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 12px;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--border-primary);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .load-more-hint {
    padding: 12px;
    text-align: center;
    color: var(--text-muted);
    font-size: 11px;
    opacity: 0.7;
  }

  /* Progress Ring */
  .progress-ring-container {
    position: relative;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .progress-ring-container.complete {
    animation: pulse-complete 0.5s ease-out;
  }

  @keyframes pulse-complete {
    0% { transform: scale(1); }
    50% { transform: scale(1.2); }
    100% { transform: scale(1); }
  }

  .progress-ring {
    width: 36px;
    height: 36px;
    transform: rotate(-90deg);
  }

  .progress-ring-bg {
    fill: none;
    stroke: var(--border-primary);
    stroke-width: 3;
  }

  .progress-ring-fill {
    fill: none;
    stroke: var(--accent-primary);
    stroke-width: 3;
    stroke-linecap: round;
    transition: stroke-dasharray 0.3s ease;
  }

  .progress-ring-container.complete .progress-ring-fill {
    stroke: var(--accent-success, #22c55e);
  }

  .progress-text {
    position: absolute;
    font-size: 8px;
    font-weight: 600;
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .untagged-count {
    color: var(--accent-warning, #f59e0b);
  }

  /* Confetti */
  .confetti-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1000;
    overflow: hidden;
  }

  .confetti {
    position: absolute;
    width: 10px;
    height: 10px;
    background: var(--color);
    top: -10px;
    left: var(--x);
    opacity: 0;
    transform: rotate(var(--rotation));
    animation: confetti-fall 3s ease-out var(--delay) forwards;
  }

  .confetti:nth-child(odd) {
    width: 8px;
    height: 12px;
    border-radius: 2px;
  }

  .confetti:nth-child(even) {
    width: 12px;
    height: 8px;
    border-radius: 50%;
  }

  @keyframes confetti-fall {
    0% {
      opacity: 1;
      top: -10px;
      transform: rotate(var(--rotation)) translateX(0);
    }
    100% {
      opacity: 0;
      top: 100vh;
      transform: rotate(calc(var(--rotation) + 720deg)) translateX(calc(var(--x) * 0.2 - 10vw));
    }
  }

  /* Modal styles */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .modal {
    background: var(--bg-secondary);
    border-radius: 8px;
    width: 450px;
    max-width: 90vw;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
  }

  .modal-title {
    font-weight: 600;
    color: var(--text-primary);
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 20px;
    color: var(--text-muted);
    cursor: pointer;
    line-height: 1;
  }

  .close-btn:hover {
    color: var(--text-primary);
  }

  .modal-body {
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .txn-preview {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 12px;
  }

  .txn-preview-date {
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .txn-preview-desc {
    flex: 1;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .txn-preview-amount {
    flex-shrink: 0;
    font-weight: 600;
  }

  .txn-preview-amount.positive {
    color: var(--accent-success, #22c55e);
  }

  .txn-preview-amount.negative {
    color: var(--accent-danger, #ef4444);
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
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
    font-size: 14px;
  }

  .form-group input:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .form-group.flex-2 {
    flex: 2;
  }

  .form-row {
    display: flex;
    gap: var(--spacing-md);
  }

  .form-row .form-group {
    flex: 1;
  }

  .amount-input {
    text-align: right;
    font-family: var(--font-mono);
  }

  .split-notice {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(var(--accent-primary-rgb, 99, 102, 241), 0.1);
    border: 1px solid var(--accent-primary);
    border-radius: 4px;
    font-size: 12px;
    color: var(--accent-primary);
  }

  .account-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 12px;
    padding-top: var(--spacing-sm);
    border-top: 1px solid var(--border-primary);
  }

  .account-label {
    color: var(--text-muted);
  }

  .account-value {
    color: var(--text-primary);
    font-weight: 500;
  }

  .account-select {
    padding: 8px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 14px;
    width: 100%;
    cursor: pointer;
  }

  .account-select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .suggested-tags {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .suggested-label {
    font-size: 11px;
    color: var(--text-muted);
  }

  .suggested-tag-btn {
    padding: 3px 8px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 3px;
    color: var(--text-primary);
    font-size: 11px;
    cursor: pointer;
  }

  .suggested-tag-btn:hover {
    background: var(--accent-primary);
    color: var(--bg-primary);
    border-color: var(--accent-primary);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    padding: var(--spacing-md) var(--spacing-lg);
    border-top: 1px solid var(--border-primary);
  }

  .btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: none;
  }

  .btn.primary {
    background: var(--accent-primary);
    color: var(--bg-primary);
  }

  .btn.secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
  }

  .btn.danger {
    background: var(--text-negative);
    color: white;
  }

  .btn:hover {
    opacity: 0.9;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .modal-actions-spacer {
    flex: 1;
  }

  /* Confirm modal */
  .confirm-overlay {
    z-index: 1001;
  }

  .confirm-modal {
    max-width: 400px;
  }

  .confirm-note {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: var(--spacing-sm);
  }

  /* Split modal */
  .split-modal {
    max-width: 500px;
  }

  .split-rows {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    margin: var(--spacing-md) 0;
  }

  .split-row {
    display: flex;
    gap: var(--spacing-sm);
    align-items: center;
  }

  .split-desc {
    flex: 2;
    padding: 8px 12px;
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 13px;
  }

  .split-amount {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 13px;
    text-align: right;
  }

  .btn-icon {
    width: 28px;
    height: 28px;
    padding: 0;
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    background: var(--bg-tertiary);
    color: var(--text-muted);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
  }

  .btn-icon:hover {
    background: var(--text-negative);
    color: white;
    border-color: var(--text-negative);
  }

  .add-split-btn {
    width: 100%;
    margin-top: var(--spacing-sm);
  }

  .split-summary {
    margin-top: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: 4px;
    font-size: 13px;
    text-align: center;
  }

  .split-summary.error {
    background: rgba(255, 100, 100, 0.15);
    color: var(--text-negative);
  }
</style>
