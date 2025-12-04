<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { executeQuery, showToast, registry } from "../../sdk";
  import { ActionBar, type ActionItem, RowMenu, type RowMenuItem } from "../../shared";
  import { FrequencyBasedSuggester } from "./suggestions";
  import type { Transaction, TagSuggestion, SplitAmount, AccountInfo } from "./types";
  import DeleteConfirmModal from "./DeleteConfirmModal.svelte";
  import UnsplitConfirmModal from "./UnsplitConfirmModal.svelte";
  import SplitTransactionModal from "./SplitTransactionModal.svelte";
  import AddTransactionModal from "./AddTransactionModal.svelte";
  import EditTransactionModal from "./EditTransactionModal.svelte";

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
  let accountsWithIds = $state<AccountInfo[]>([]);
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

  // Undo stack for tag operations
  interface UndoEntry {
    transactionId: string;
    previousTags: string[];
    newTags: string[];
  }
  let undoStack = $state<UndoEntry[][]>([]); // Each entry is an array of changes (for bulk ops)
  const MAX_UNDO_DEPTH = 20;

  // Transaction edit modal
  let isTagModalOpen = $state(false);
  let editingTransaction = $state<Transaction | null>(null);
  // Delete confirmation
  let showDeleteConfirm = $state(false);

  // Split modal
  let showSplitModal = $state(false);

  // Row context menu
  let contextMenuTxn = $state<Transaction | null>(null);

  function getRowMenuItems(txn: Transaction): RowMenuItem[] {
    const items: RowMenuItem[] = [
      { label: "Edit", action: () => handleContextEdit() },
    ];

    if (txn.parent_transaction_id) {
      items.push({ label: "Unsplit", action: () => handleContextUnsplit() });
    } else {
      items.push({ label: "Split", action: () => handleContextSplit() });
    }

    items.push({ label: "Delete", action: () => handleContextDelete(), danger: true });

    return items;
  }

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

  // Autocomplete for bulk tag input
  let bulkTagAutocomplete = $derived.by(() => {
    if (!bulkTagInput || allTags.length === 0) return "";

    // Get the partial tag being typed (after last comma)
    const parts = bulkTagInput.split(",");
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
        t.transaction_id,
        t.account_id,
        t.transaction_date,
        t.description,
        t.amount,
        t.tags,
        t.account_name,
        t.parent_transaction_id,
        a.nickname as account_nickname
      FROM transactions t
      LEFT JOIN sys_accounts a ON t.account_id = a.account_id
    `;

    const conditions: string[] = [];

    // Account filter (multi-select)
    if (selectedAccounts.size > 0) {
      const accountList = Array.from(selectedAccounts)
        .map(a => `'${a.replace(/'/g, "''")}'`)
        .join(", ");
      conditions.push(`t.account_name IN (${accountList})`);
    }

    // Untagged filter - works alongside search
    if (filterMode === "untagged") {
      conditions.push("t.tags = []");
    }

    // Search filter
    if (searchQuery.trim()) {
      const escapedSearch = searchQuery.trim().replace(/'/g, "''");
      // Search across description, account_name, amount (as string), and tags
      conditions.push(`(
        t.description ILIKE '%${escapedSearch}%'
        OR t.account_name ILIKE '%${escapedSearch}%'
        OR CAST(t.amount AS VARCHAR) LIKE '%${escapedSearch}%'
        OR array_to_string(t.tags, ',') ILIKE '%${escapedSearch}%'
      )`);
    }

    if (conditions.length > 0) {
      query += " WHERE " + conditions.join(" AND ");
    }

    query += ` ORDER BY t.transaction_date DESC LIMIT ${PAGE_SIZE + 1} OFFSET ${offset}`;
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
      account_nickname: row[8] as string | null,
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
      e.stopPropagation();
      // Immediately execute search and exit search mode
      if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
      }
      loadTransactions();
      exitSearch();
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
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

    // Ctrl+Z / Cmd+Z to undo
    if ((e.ctrlKey || e.metaKey) && e.key === "z") {
      e.preventDefault();
      performUndo();
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
      case "e":
        e.preventDefault();
        if (transactions[cursorIndex]) {
          openTagModal(transactions[cursorIndex]);
        }
        break;
      case "d":
        e.preventDefault();
        if (transactions[cursorIndex]) {
          deleteCurrentTransaction();
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
      // Apply autocomplete suggestion
      if (bulkTagAutocomplete) {
        bulkTagInput += bulkTagAutocomplete;
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
    searchInputEl?.focus();
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

    // Record undo entries before making changes
    const undoEntries: UndoEntry[] = [];

    // Optimistic update - update local state immediately
    for (const idx of indices) {
      const txn = transactions[idx];
      if (!txn) continue;
      const currentTags = txn.tags || [];
      if (currentTags.includes(tag)) continue;

      // Record for undo
      const newTags = [...currentTags, tag];
      undoEntries.push({
        transactionId: txn.transaction_id,
        previousTags: [...currentTags],
        newTags: newTags
      });

      // Update in place
      transactions[idx] = {
        ...txn,
        tags: newTags
      };
    }

    // Push to undo stack
    pushUndo(undoEntries);

    // Force reactivity
    transactions = [...transactions];

    // Don't auto-advance cursor - let users apply multiple tags to the same transaction
    // They can press j/k to move manually when ready

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

  // Push a batch of tag changes to the undo stack
  function pushUndo(entries: UndoEntry[]) {
    if (entries.length === 0) return;
    undoStack = [...undoStack.slice(-(MAX_UNDO_DEPTH - 1)), entries];
  }

  // Undo the last tag operation
  async function performUndo() {
    if (undoStack.length === 0) {
      showToast("Nothing to undo", "info");
      return;
    }

    const entries = undoStack[undoStack.length - 1];
    undoStack = undoStack.slice(0, -1);

    // Apply reverts locally
    for (const entry of entries) {
      const idx = transactions.findIndex(t => t.transaction_id === entry.transactionId);
      if (idx >= 0) {
        transactions[idx] = {
          ...transactions[idx],
          tags: [...entry.previousTags]
        };
      }
    }

    transactions = [...transactions];

    // Persist the reverted tags
    const txnsToUpdate = entries
      .map(e => transactions.find(t => t.transaction_id === e.transactionId))
      .filter((t): t is Transaction => t !== undefined);

    await persistTagChanges(txnsToUpdate);
    showToast(`Undid ${entries.length} tag change${entries.length > 1 ? 's' : ''}`, "success");
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

    // Record undo entries before making changes
    const undoEntries: UndoEntry[] = [];

    // Optimistic update
    for (const idx of indices) {
      const txn = transactions[idx];
      if (!txn) continue;

      // Merge tags (dedupe)
      const currentTags = txn.tags || [];
      const mergedTags = [...new Set([...currentTags, ...tags])];

      // Record for undo
      undoEntries.push({
        transactionId: txn.transaction_id,
        previousTags: [...currentTags],
        newTags: mergedTags
      });

      transactions[idx] = {
        ...txn,
        tags: mergedTags
      };
    }

    // Push to undo stack
    pushUndo(undoEntries);

    transactions = [...transactions];

    // Don't auto-advance - consistent with quick tag behavior
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

    // Record undo entries before making changes
    const undoEntries: UndoEntry[] = [];

    // Apply to ALL visible transactions
    for (let i = 0; i < transactions.length; i++) {
      const txn = transactions[i];
      const currentTags = txn.tags || [];
      const mergedTags = [...new Set([...currentTags, ...tags])];

      // Record for undo
      undoEntries.push({
        transactionId: txn.transaction_id,
        previousTags: [...currentTags],
        newTags: mergedTags
      });

      transactions[i] = {
        ...txn,
        tags: mergedTags
      };
    }

    // Push to undo stack
    pushUndo(undoEntries);

    transactions = [...transactions];
    cancelBulkTagging();

    // Persist all in background
    persistTagChanges(transactions);
  }

  // Clear all tags (set to empty)
  async function clearTagsFromCurrent() {
    const indices = getSelectedIndicesArray();
    if (indices.length === 0) return;

    // Record undo entries before making changes
    const undoEntries: UndoEntry[] = [];

    // Optimistic update
    for (const idx of indices) {
      const txn = transactions[idx];
      if (!txn || txn.tags.length === 0) continue;

      // Record for undo
      undoEntries.push({
        transactionId: txn.transaction_id,
        previousTags: [...txn.tags],
        newTags: []
      });

      transactions[idx] = {
        ...txn,
        tags: []
      };
    }

    // Push to undo stack
    pushUndo(undoEntries);

    transactions = [...transactions];

    // Don't auto-advance - consistent with quick tag behavior
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
    isTagModalOpen = true;
  }

  function closeTagModal() {
    isTagModalOpen = false;
    editingTransaction = null;
    containerEl?.focus();
  }

  // Row context menu functions
  function openContextMenu(txn: Transaction, e: MouseEvent) {
    e.stopPropagation();
    contextMenuTxn = txn;
  }

  function closeContextMenu() {
    contextMenuTxn = null;
  }

  function handleContextEdit() {
    if (contextMenuTxn) {
      openTagModal(contextMenuTxn);
    }
    closeContextMenu();
  }

  function handleContextDelete() {
    if (contextMenuTxn) {
      editingTransaction = contextMenuTxn;
      showDeleteConfirm = true;
    }
    closeContextMenu();
  }

  function handleContextSplit() {
    if (contextMenuTxn) {
      // Check if it's already a split child - can't split a split
      if (contextMenuTxn.parent_transaction_id) {
        showToast("Cannot split a transaction that is already part of a split", "error");
        closeContextMenu();
        return;
      }
      editingTransaction = contextMenuTxn;
      openSplitModal();
    }
    closeContextMenu();
  }

  function handleContextUnsplit() {
    if (contextMenuTxn && contextMenuTxn.parent_transaction_id) {
      editingTransaction = contextMenuTxn;
      showUnsplitConfirm = true;
    }
    closeContextMenu();
  }

  async function handleEditSave(data: {
    description: string;
    amount: number;
    date: string;
    tags: string[];
  }) {
    if (!editingTransaction) return;

    // Find the transaction in our list and update it
    const idx = transactions.findIndex(t => t.transaction_id === editingTransaction!.transaction_id);
    if (idx >= 0) {
      transactions[idx] = {
        ...transactions[idx],
        tags: data.tags,
        description: data.description,
        amount: data.amount,
        transaction_date: data.date
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

  // Delete current transaction (keyboard shortcut)
  function deleteCurrentTransaction() {
    const txn = transactions[cursorIndex];
    if (!txn) return;
    // Open modal and show delete confirmation
    openTagModal(txn);
    showDeleteConfirm = true;
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
    showSplitModal = true;
  }

  function closeSplitModal() {
    showSplitModal = false;
  }

  function generateUUID(): string {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  async function handleSplit(splitAmounts: SplitAmount[]) {
    if (!editingTransaction) return;

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
    showAddModal = true;
  }

  function closeAddModal() {
    showAddModal = false;
    containerEl?.focus();
  }

  async function handleAddTransaction(data: {
    description: string;
    amount: number;
    date: string;
    accountId: string;
    tags: string[];
  }) {
    try {
      const now = new Date().toISOString();
      const txnId = generateUUID();
      const escapedDesc = data.description.replace(/'/g, "''");

      // Find account name for the selected account
      const selectedAccount = accountsWithIds.find(a => a.id === data.accountId);
      const accountName = selectedAccount?.name || "";

      await executeQuery(
        `INSERT INTO sys_transactions (
          transaction_id, account_id, amount, description,
          transaction_date, posted_date, tags, external_ids,
          created_at, updated_at
        ) VALUES (
          '${txnId}',
          '${data.accountId}',
          ${data.amount},
          '${escapedDesc}',
          '${data.date}',
          '${data.date}',
          ${data.tags.length > 0 ? `ARRAY[${data.tags.map((t) => `'${t}'`).join(",")}]` : "NULL"},
          '{"manual": true}',
          '${now}',
          '${now}'
        )`,
        { readonly: false }
      );

      // Add to local list
      const newTxn: Transaction = {
        transaction_id: txnId,
        account_id: data.accountId,
        account_name: accountName,
        amount: data.amount,
        description: data.description,
        transaction_date: data.date,
        tags: data.tags,
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

  // Action bar items
  let actionBarItems = $derived<ActionItem[]>([
    { keys: ["j", "k"], label: "nav", action: () => {} },
    { keys: ["e"], label: "edit", action: () => transactions[cursorIndex] && openTagModal(transactions[cursorIndex]) },
    { keys: ["d"], label: "delete", action: deleteCurrentTransaction },
    { keys: ["a"], label: "bulk tag", action: startBulkTagging },
    { keys: ["t"], label: "tag", action: startCustomTagging },
    { keys: ["/"], label: "search", action: startSearch },
    { keys: ["u"], label: "untagged", action: toggleFilterMode },
    { keys: ["n"], label: "next untagged", action: skipToNextUntagged },
    { keys: ["⌘Z"], label: "undo", action: performUndo },
  ]);

  // Subscribe to global refresh events
  let unsubscribeRefresh: (() => void) | null = null;

  async function reloadAll() {
    await suggester.loadTagData();
    allTags = suggester.getAllTags();
    await Promise.all([loadGlobalStats(), loadAvailableAccounts()]);
    await loadTransactions();
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

    // Listen for data refresh events (e.g., demo mode toggle)
    unsubscribeRefresh = registry.on("data:refresh", () => {
      reloadAll();
    });
  });

  onDestroy(() => {
    unsubscribeRefresh?.();
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

  <!-- Context menu backdrop -->
  {#if contextMenuTxn}
    <button class="context-menu-backdrop" onclick={closeContextMenu}></button>
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

      <!-- Search box - always visible -->
      <div class="header-search">
        <span class="search-icon">⌕</span>
        <input
          bind:this={searchInputEl}
          type="text"
          class="header-search-input"
          bind:value={searchQuery}
          oninput={handleSearchInput}
          onkeydown={handleSearchKeyDown}
          onfocus={() => isSearching = true}
          onblur={() => isSearching = false}
          placeholder="Search... (/)"
        />
        {#if searchQuery}
          <button class="clear-search" onclick={clearSearch}>×</button>
        {/if}
      </div>

      <!-- Filter mode indicator -->
      {#if filterMode === "untagged"}
        <button class="mode-btn untagged-mode" onclick={toggleFilterMode} title="Press 'u' to toggle">
          Untagged Only
        </button>
      {:else}
        <button class="mode-btn" onclick={toggleFilterMode} title="Press 'u' to show only untagged">
          All
        </button>
      {/if}

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

  <ActionBar actions={actionBarItems} />

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
            <div class="row-date">{txn.transaction_date}</div>
            <div class="row-account">{txn.account_nickname || txn.account_name || ''}</div>
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
            <RowMenu
              items={getRowMenuItems(txn)}
              isOpen={contextMenuTxn?.transaction_id === txn.transaction_id}
              onToggle={(e) => openContextMenu(txn, e)}
              onClose={closeContextMenu}
              title="Transaction actions"
            />
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

    <!-- Sidebar -->
    <div class="sidebar">
      <!-- Quick Tags (actionable) -->
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

      <!-- Transaction Info (details + current tags) -->
      {#if currentTxn}
        <div class="sidebar-section txn-details">
          <div class="sidebar-title">Selected Transaction</div>
          <div class="txn-details-content">
            <div class="txn-detail-row">
              <span class="txn-detail-label">Date</span>
              <span class="txn-detail-value">{currentTxn.transaction_date}</span>
            </div>
            <div class="txn-detail-row">
              <span class="txn-detail-label">Account</span>
              <span class="txn-detail-value">{currentTxn.account_nickname || currentTxn.account_name || 'Unknown'}</span>
            </div>
            <div class="txn-detail-row">
              <span class="txn-detail-label">Amount</span>
              <span class="txn-detail-value" class:negative={currentTxn.amount < 0} class:positive={currentTxn.amount >= 0}>
                {currentTxn.amount < 0 ? '-' : ''}${formatAmount(currentTxn.amount)}
              </span>
            </div>
            <div class="txn-detail-desc">
              <span class="txn-detail-label">Description</span>
              <span class="txn-detail-value desc">{currentTxn.description}</span>
            </div>
            {#if currentTxn.tags.length > 0}
              <div class="txn-detail-tags">
                <span class="txn-detail-label">Tags</span>
                <div class="current-tags">
                  {#each currentTxn.tags as tag}
                    <span class="current-tag">{tag}</span>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Split Transaction Info -->
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
  <div class="command-bar" class:active={isCustomTagging || isBulkTagging}>
    {#if isCustomTagging}
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
        <span class="input-wrapper">
          <input
            bind:this={bulkTagInputEl}
            type="text"
            class="command-input"
            bind:value={bulkTagInput}
            placeholder="apply to ALL visible transactions"
          />{#if bulkTagAutocomplete}<span class="autocomplete-hint" style="left: {bulkTagInput.length}ch">{bulkTagAutocomplete}</span>{/if}
        </span>
        <span class="command-hint">Tab complete | Enter apply | Esc cancel</span>
      </div>
    {/if}
  </div>
</div>

<!-- Modals -->
<EditTransactionModal
  open={isTagModalOpen && !!editingTransaction}
  transaction={editingTransaction}
  suggestions={currentSuggestions}
  onclose={closeTagModal}
  onsave={handleEditSave}
/>

<UnsplitConfirmModal
  open={showUnsplitConfirm && !!editingTransaction}
  onclose={() => showUnsplitConfirm = false}
  onconfirm={unsplitTransaction}
/>

<DeleteConfirmModal
  open={showDeleteConfirm && !!editingTransaction}
  transaction={editingTransaction}
  onclose={() => showDeleteConfirm = false}
  onconfirm={deleteTransaction}
/>

<SplitTransactionModal
  open={showSplitModal && !!editingTransaction}
  transaction={editingTransaction}
  onclose={closeSplitModal}
  onsplit={handleSplit}
/>

<AddTransactionModal
  open={showAddModal}
  accounts={accountsWithIds}
  onclose={closeAddModal}
  onsave={handleAddTransaction}
/>

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

  /* Header search box */
  .header-search {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    min-width: 180px;
  }

  .header-search:focus-within {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1);
  }

  .search-icon {
    color: var(--text-muted);
    font-size: 14px;
    flex-shrink: 0;
  }

  .header-search-input {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-size: 12px;
    outline: none;
    min-width: 0;
  }

  .header-search-input::placeholder {
    color: var(--text-muted);
  }

  .clear-search {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 14px;
    padding: 0 2px;
    line-height: 1;
  }

  .clear-search:hover {
    color: var(--text-primary);
  }

  /* Filter mode button */
  .mode-btn {
    padding: 4px 10px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
  }

  .mode-btn:hover {
    border-color: var(--accent-primary);
  }

  .mode-btn.untagged-mode {
    background: var(--accent-danger, #ef4444);
    color: white;
    border-color: var(--accent-danger, #ef4444);
  }

  .mode-btn.untagged-mode:hover {
    opacity: 0.9;
  }

  /* Account filter dropdown */
  .account-filter-container {
    position: relative;
    margin-left: auto; /* Push to right side of header */
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

  .txn-details-content {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .txn-detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
  }

  .txn-detail-desc,
  .txn-detail-tags {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 12px;
    margin-top: var(--spacing-xs);
  }

  .txn-detail-tags .current-tags {
    margin-top: 4px;
  }

  .txn-detail-label {
    color: var(--text-muted);
    font-size: 11px;
  }

  .txn-detail-value {
    color: var(--text-primary);
  }

  .txn-detail-value.desc {
    word-break: break-word;
    line-height: 1.4;
  }

  .txn-detail-value.negative {
    color: var(--amount-negative, #ef4444);
  }

  .txn-detail-value.positive {
    color: var(--amount-positive, #22c55e);
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

  /* Split transaction styles - subtle box grouping */
  .row.split-child {
    position: relative;
    border-left: 1px solid var(--border-primary);
    border-right: 1px solid var(--border-primary);
    margin-left: 8px;
    margin-right: 8px;
    border-bottom: none;
  }

  .row.split-child:not(.split-last) {
    border-bottom: 1px dashed var(--border-primary);
  }

  .row.split-first {
    border-top: 1px solid var(--border-primary);
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-top: 4px;
  }

  .row.split-last {
    border-bottom: 1px solid var(--border-primary);
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    margin-bottom: 4px;
  }

  .split-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    color: var(--text-muted);
    margin-right: 4px;
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

</style>
