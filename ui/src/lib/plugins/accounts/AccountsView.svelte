<script lang="ts">
  import { onMount } from "svelte";
  import {
    executeQuery,
    registry,
    getPluginSettings,
    setPluginSettings,
    pickCsvFile,
    getCsvHeaders,
    importCsvPreview,
    importCsvExecute,
    showToast,
  } from "../../sdk";
  import { ActionBar, type ActionItem, Modal, RowMenu, type RowMenuItem } from "../../shared";
  import type { ImportColumnMapping, ImportPreviewResult, ImportExecuteResult } from "../../sdk";
  import type {
    AccountWithStats,
    BalanceClassification,
    BalanceTrendPoint,
    AccountsConfig,
  } from "./types";
  import { getDefaultClassification } from "./types";

  // Props (passed from openView)
  interface Props {
    action?: "add";
  }
  let { action }: Props = $props();

  const PLUGIN_ID = "accounts";

  // State
  let accounts = $state<AccountWithStats[]>([]);
  let isLoading = $state(true);
  let error = $state<string | null>(null);
  let config = $state<AccountsConfig>({
    classificationOverrides: {},
    excludedFromNetWorth: [],
  });

  // Navigation
  let cursorIndex = $state(0);
  let containerEl: HTMLDivElement | null = null;

  // "As of" date for viewing historical balances
  let referenceDate = $state(new Date());
  let referenceDay = $derived(referenceDate.getDate());
  let referenceDateStr = $derived(
    referenceDate.toLocaleDateString("en-US", { month: "long", day: "numeric" })
  );
  let isToday = $derived(
    referenceDate.toDateString() === new Date().toDateString()
  );

  // Date picker
  function goToToday() {
    referenceDate = new Date();
  }

  // Transaction preview modal
  interface PreviewTransaction {
    transaction_id: string;
    transaction_date: string;
    description: string;
    amount: number;
    tags: string[];
  }
  let showTransactionPreview = $state(false);
  let previewAccount = $state<AccountWithStats | null>(null);
  let previewTransactions = $state<PreviewTransaction[]>([]);
  let previewLoading = $state(false);

  // Balance trend for selected account (shown in sidebar)
  let balanceTrend = $state<BalanceTrendPoint[]>([]);

  // Net worth trend for MoM calculation (aggregates all accounts)
  let netWorthTrend = $state<{ month: string; netWorth: number }[]>([]);

  // Edit modal
  let isEditing = $state(false);
  let editingAccount = $state<AccountWithStats | null>(null);
  let editForm = $state({
    nickname: "",
    account_type: "",
    classification: "asset" as BalanceClassification,
    excluded_from_net_worth: false,
  });

  // Add account modal
  let isAddingAccount = $state(false);
  let addAccountForm = $state({
    name: "",
    nickname: "",
    account_type: "",
    classification: "asset" as BalanceClassification,
    initial_balance: "",
    institution_name: "",
  });

  // Account row menu
  let menuOpenForAccount = $state<string | null>(null);

  // CSV Import modal
  let showImportModal = $state(false);
  let importAccountId = $state("");
  let importAccountName = $state("");
  let importFilePath = $state("");
  let importFileName = $state("");
  let importHeaders = $state<string[]>([]);
  let importColumnMapping = $state<ImportColumnMapping>({});
  let importFlipSigns = $state(false);
  let importDebitNegative = $state(false);
  let importPreview = $state<ImportPreviewResult | null>(null);
  let importResult = $state<ImportExecuteResult | null>(null);
  let importError = $state<string | null>(null);
  let isImporting = $state(false);
  let isLoadingPreview = $state(false);
  let previewDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  // Derived: split accounts by classification
  let assetAccounts = $derived(accounts.filter((a) => a.classification === "asset"));
  let liabilityAccounts = $derived(accounts.filter((a) => a.classification === "liability"));

  // Flat list for navigation (assets first, then liabilities)
  let allAccounts = $derived([...assetAccounts, ...liabilityAccounts]);

  let currentAccount = $derived(allAccounts[cursorIndex]);

  // Totals
  let totalAssets = $derived(
    assetAccounts
      .filter((a) => !config.excludedFromNetWorth.includes(a.account_id))
      .reduce((sum, a) => sum + (a.balance ?? a.computed_balance), 0)
  );
  let totalLiabilities = $derived(
    liabilityAccounts
      .filter((a) => !config.excludedFromNetWorth.includes(a.account_id))
      .reduce((sum, a) => sum + Math.abs(a.balance ?? a.computed_balance), 0)
  );
  let netWorth = $derived(totalAssets - totalLiabilities);

  // Month-over-month net worth change
  let momChange = $derived.by(() => {
    if (netWorthTrend.length < 2) return null;
    const current = netWorthTrend[netWorthTrend.length - 1]?.netWorth ?? 0;
    const previous = netWorthTrend[netWorthTrend.length - 2]?.netWorth ?? 0;
    const change = current - previous;
    const percent = previous !== 0 ? (change / Math.abs(previous)) * 100 : 0;
    return { change, percent };
  });

  const DEFAULT_CONFIG: AccountsConfig = {
    classificationOverrides: {},
    excludedFromNetWorth: [],
  };

  async function loadConfig(): Promise<AccountsConfig> {
    return getPluginSettings<AccountsConfig>(PLUGIN_ID, DEFAULT_CONFIG);
  }

  async function saveConfig(newConfig: AccountsConfig): Promise<void> {
    await setPluginSettings(PLUGIN_ID, newConfig);
    config = newConfig;
  }

  async function loadAccounts() {
    isLoading = true;
    error = null;

    try {
      config = await loadConfig();

      // Format reference date for SQL query (end of day)
      const refDateStr = `${referenceDate.getFullYear()}-${String(referenceDate.getMonth() + 1).padStart(2, "0")}-${String(referenceDate.getDate()).padStart(2, "0")} 23:59:59`;

      // Load accounts with balances as of the reference date
      const result = await executeQuery(`
        WITH snapshots_as_of AS (
          SELECT
            account_id,
            balance,
            snapshot_time,
            ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY snapshot_time DESC) as rn
          FROM balance_snapshots
          WHERE snapshot_time <= '${refDateStr}'
        ),
        account_stats AS (
          SELECT
            account_id,
            COUNT(*) as transaction_count,
            MIN(transaction_date) as first_transaction,
            MAX(transaction_date) as last_transaction
          FROM transactions
          GROUP BY account_id
        )
        SELECT
          a.account_id,
          a.name,
          a.nickname,
          a.account_type,
          a.currency,
          s_ao.balance as balance_as_of_date,
          a.institution_name,
          a.created_at,
          a.updated_at,
          COALESCE(s.transaction_count, 0) as transaction_count,
          s.first_transaction,
          s.last_transaction,
          s_ao.snapshot_time as balance_as_of
        FROM accounts a
        LEFT JOIN snapshots_as_of s_ao ON a.account_id = s_ao.account_id AND s_ao.rn = 1
        LEFT JOIN account_stats s ON a.account_id = s.account_id
        ORDER BY a.name
      `);

      accounts = result.rows.map((row) => {
        const accountId = row[0] as string;
        const accountType = row[3] as string | null;
        const classification =
          config.classificationOverrides[accountId] ??
          getDefaultClassification(accountType);

        return {
          account_id: accountId,
          name: row[1] as string,
          nickname: row[2] as string | null,
          account_type: accountType,
          currency: row[4] as string,
          balance: row[5] as number | null,
          institution_name: row[6] as string | null,
          created_at: row[7] as string,
          updated_at: row[8] as string,
          transaction_count: (row[9] as number) ?? 0,
          first_transaction: row[10] as string | null,
          last_transaction: row[11] as string | null,
          computed_balance: 0, // Not used anymore, using snapshot balance
          balance_as_of: row[12] as string | null,
          classification,
        };
      });

      // Reset cursor if needed
      if (cursorIndex >= allAccounts.length) {
        cursorIndex = Math.max(0, allAccounts.length - 1);
      }

      // Load net worth trend for MoM calculation
      await loadNetWorthTrend();

      // Load trend for current account
      if (currentAccount) {
        await loadBalanceTrend(currentAccount.account_id);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load accounts";
      console.error("Failed to load accounts:", e);
    } finally {
      isLoading = false;
    }
  }

  async function loadBalanceTrend(accountId: string) {
    const day = referenceDay;
    const trends: BalanceTrendPoint[] = [];

    // Format reference date for SQL query (end of day)
    const refDateStr = `${referenceDate.getFullYear()}-${String(referenceDate.getMonth() + 1).padStart(2, "0")}-${String(referenceDate.getDate()).padStart(2, "0")} 23:59:59`;

    // Get snapshots for this account up to reference date
    const result = await executeQuery(`
      SELECT
        snapshot_id,
        account_id,
        balance,
        snapshot_time
      FROM balance_snapshots
      WHERE account_id = '${accountId}'
        AND snapshot_time <= '${refDateStr}'
      ORDER BY snapshot_time DESC
    `);

    if (result.rows.length === 0) {
      balanceTrend = [];
      return;
    }

    // Group snapshots by month and find the one closest to our reference day
    const snapshotsByMonth = new Map<string, { balance: number; snapshot_time: string; day: number }[]>();

    for (const row of result.rows) {
      const snapshotTime = new Date(row[3] as string);
      const monthKey = `${snapshotTime.getFullYear()}-${String(snapshotTime.getMonth() + 1).padStart(2, "0")}`;
      const snapshotDay = snapshotTime.getDate();

      if (!snapshotsByMonth.has(monthKey)) {
        snapshotsByMonth.set(monthKey, []);
      }
      snapshotsByMonth.get(monthKey)!.push({
        balance: row[2] as number,
        snapshot_time: row[3] as string,
        day: snapshotDay,
      });
    }

    // For each of the last 6 months relative to reference date, find the snapshot closest to our reference day
    for (let i = 0; i < 6; i++) {
      const targetDate = new Date(referenceDate.getFullYear(), referenceDate.getMonth() - i, 1);
      const monthKey = `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, "0")}`;
      const daysInMonth = new Date(targetDate.getFullYear(), targetDate.getMonth() + 1, 0).getDate();
      const targetDay = Math.min(day, daysInMonth);

      const monthSnapshots = snapshotsByMonth.get(monthKey);
      if (monthSnapshots && monthSnapshots.length > 0) {
        // Find snapshot closest to target day
        let closest = monthSnapshots[0];
        let closestDiff = Math.abs(closest.day - targetDay);

        for (const snap of monthSnapshots) {
          const diff = Math.abs(snap.day - targetDay);
          if (diff < closestDiff) {
            closest = snap;
            closestDiff = diff;
          }
        }

        trends.unshift({
          month: monthKey,
          day: closest.day,
          balance: closest.balance,
          snapshot_time: closest.snapshot_time,
        });
      }
    }

    balanceTrend = trends;
  }

  async function loadNetWorthTrend() {
    const day = referenceDay;
    const excludedIds = config.excludedFromNetWorth;

    // Get all snapshots for all accounts
    const result = await executeQuery(`
      SELECT
        bs.account_id,
        bs.balance,
        bs.snapshot_time,
        a.account_type
      FROM balance_snapshots bs
      JOIN accounts a ON bs.account_id = a.account_id
      ORDER BY bs.snapshot_time DESC
    `);

    if (result.rows.length === 0) {
      netWorthTrend = [];
      return;
    }

    // Group snapshots by account and month
    // Map: account_id -> month -> snapshots[]
    const snapshotsByAccountMonth = new Map<string, Map<string, { balance: number; day: number; accountType: string }[]>>();

    for (const row of result.rows) {
      const accountId = row[0] as string;
      if (excludedIds.includes(accountId)) continue;

      const balance = row[1] as number;
      const snapshotTime = new Date(row[2] as string);
      const accountType = row[3] as string | null;
      const monthKey = `${snapshotTime.getFullYear()}-${String(snapshotTime.getMonth() + 1).padStart(2, "0")}`;
      const snapshotDay = snapshotTime.getDate();

      if (!snapshotsByAccountMonth.has(accountId)) {
        snapshotsByAccountMonth.set(accountId, new Map());
      }
      const accountMonths = snapshotsByAccountMonth.get(accountId)!;
      if (!accountMonths.has(monthKey)) {
        accountMonths.set(monthKey, []);
      }
      accountMonths.get(monthKey)!.push({
        balance,
        day: snapshotDay,
        accountType: accountType || "",
      });
    }

    // For each of the last 6 months, calculate net worth
    const trends: { month: string; netWorth: number }[] = [];
    const now = new Date();

    for (let i = 0; i < 6; i++) {
      const targetDate = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const monthKey = `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, "0")}`;
      const daysInMonth = new Date(targetDate.getFullYear(), targetDate.getMonth() + 1, 0).getDate();
      const targetDay = Math.min(day, daysInMonth);

      let monthNetWorth = 0;
      let hasData = false;

      for (const [accountId, accountMonths] of snapshotsByAccountMonth) {
        const monthSnapshots = accountMonths.get(monthKey);
        if (monthSnapshots && monthSnapshots.length > 0) {
          hasData = true;
          // Find snapshot closest to target day
          let closest = monthSnapshots[0];
          let closestDiff = Math.abs(closest.day - targetDay);

          for (const snap of monthSnapshots) {
            const diff = Math.abs(snap.day - targetDay);
            if (diff < closestDiff) {
              closest = snap;
              closestDiff = diff;
            }
          }

          // Check classification (use config override or default)
          const classification =
            config.classificationOverrides[accountId] ??
            getDefaultClassification(closest.accountType);

          if (classification === "liability") {
            monthNetWorth -= Math.abs(closest.balance);
          } else {
            monthNetWorth += closest.balance;
          }
        }
      }

      if (hasData) {
        trends.unshift({ month: monthKey, netWorth: monthNetWorth });
      }
    }

    netWorthTrend = trends;
  }

  // Effect: load trend when account changes
  $effect(() => {
    if (currentAccount && !isLoading) {
      loadBalanceTrend(currentAccount.account_id);
    }
  });

  // Effect: reload accounts when reference date changes
  let previousRefDate: string | null = null;
  $effect(() => {
    const currentRefDate = referenceDate.toISOString().split("T")[0];
    if (previousRefDate !== null && previousRefDate !== currentRefDate) {
      loadAccounts();
    }
    previousRefDate = currentRefDate;
  });

  function handleKeyDown(e: KeyboardEvent) {
    if (isEditing || showTransactionPreview || isAddingAccount) return;

    switch (e.key) {
      case "j":
      case "ArrowDown":
        e.preventDefault();
        if (cursorIndex < allAccounts.length - 1) cursorIndex++;
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
        if (currentAccount) {
          showPreview(currentAccount);
        }
        break;
      case "e":
        e.preventDefault();
        if (currentAccount) startEdit(currentAccount);
        break;
      case "a":
        e.preventDefault();
        startAddAccount();
        break;
      case "h":
      case "ArrowLeft":
        e.preventDefault();
        cycleDay(-1);
        break;
      case "l":
      case "ArrowRight":
        e.preventDefault();
        cycleDay(1);
        break;
      case "r":
        e.preventDefault();
        loadAccounts();
        break;
      case "t":
        e.preventDefault();
        goToToday();
        break;
      case "g":
        e.preventDefault();
        cursorIndex = 0;
        scrollToCursor();
        break;
      case "G":
        e.preventDefault();
        cursorIndex = allAccounts.length - 1;
        scrollToCursor();
        break;
      case "d":
        e.preventDefault();
        if (currentAccount) deleteAccount(currentAccount);
        break;
    }
  }

  function cycleDay(delta: number) {
    const newDate = new Date(referenceDate);
    newDate.setDate(newDate.getDate() + delta);
    // Don't go into the future
    if (newDate <= new Date()) {
      referenceDate = newDate;
    }
  }

  function handleDateChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.value) {
      const [year, month, day] = input.value.split("-").map(Number);
      const newDate = new Date(year, month - 1, day);
      if (newDate <= new Date()) {
        referenceDate = newDate;
      }
    }
    containerEl?.focus();
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
    const account = allAccounts[index];
    if (account) {
      showPreview(account);
    }
  }

  async function showPreview(account: AccountWithStats) {
    previewAccount = account;
    previewLoading = true;
    showTransactionPreview = true;
    previewTransactions = [];

    try {
      const accountName = account.name.replace(/'/g, "''");
      const result = await executeQuery(`
        SELECT
          transaction_id,
          transaction_date,
          description,
          amount,
          tags
        FROM transactions
        WHERE account_name = '${accountName}'
        ORDER BY transaction_date DESC
        LIMIT 50
      `);

      previewTransactions = result.rows.map((row) => ({
        transaction_id: row[0] as string,
        transaction_date: row[1] as string,
        description: row[2] as string,
        amount: row[3] as number,
        tags: (row[4] as string[]) || [],
      }));
    } catch (e) {
      console.error("Failed to load transactions:", e);
    } finally {
      previewLoading = false;
    }
  }

  function closePreview() {
    showTransactionPreview = false;
    previewAccount = null;
    previewTransactions = [];
    containerEl?.focus();
  }

  function editFromPreview() {
    const account = previewAccount;
    closePreview();
    if (account) startEdit(account);
  }

  function openInQuery() {
    if (!previewAccount) return;
    const accountName = previewAccount.name.replace(/'/g, "''");
    const query = `SELECT transaction_date, description, amount, tags
FROM transactions
WHERE account_name = '${accountName}'
ORDER BY transaction_date DESC
LIMIT 100`;
    registry.openView("query", { initialQuery: query });
    closePreview();
  }

  function startEdit(account: AccountWithStats) {
    editingAccount = account;
    editForm = {
      nickname: account.nickname || "",
      account_type: account.account_type || "",
      classification: account.classification,
      excluded_from_net_worth: config.excludedFromNetWorth.includes(account.account_id),
    };
    isEditing = true;
  }

  function cancelEdit() {
    isEditing = false;
    editingAccount = null;
    containerEl?.focus();
  }

  async function saveEdit() {
    if (!editingAccount) return;

    try {
      // Update nickname and account_type in database
      const nicknameValue = editForm.nickname.trim() || null;
      const typeValue = editForm.account_type.trim() || null;

      await executeQuery(
        `UPDATE sys_accounts SET
          nickname = ${nicknameValue ? `'${nicknameValue.replace(/'/g, "''")}'` : "NULL"},
          account_type = ${typeValue ? `'${typeValue.replace(/'/g, "''")}'` : "NULL"},
          updated_at = CURRENT_TIMESTAMP
        WHERE account_id = '${editingAccount.account_id}'`,
        { readonly: false }
      );

      // Update config for classification override and exclusion
      const newConfig = { ...config };

      // Handle classification override
      const defaultClass = getDefaultClassification(typeValue);
      if (editForm.classification !== defaultClass) {
        newConfig.classificationOverrides[editingAccount.account_id] = editForm.classification;
      } else {
        delete newConfig.classificationOverrides[editingAccount.account_id];
      }

      // Handle net worth exclusion
      if (editForm.excluded_from_net_worth) {
        if (!newConfig.excludedFromNetWorth.includes(editingAccount.account_id)) {
          newConfig.excludedFromNetWorth.push(editingAccount.account_id);
        }
      } else {
        newConfig.excludedFromNetWorth = newConfig.excludedFromNetWorth.filter(
          (id) => id !== editingAccount.account_id
        );
      }

      await saveConfig(newConfig);

      cancelEdit();
      await loadAccounts();
    } catch (e) {
      console.error("Failed to save account:", e);
      error = e instanceof Error ? e.message : "Failed to save account";
    }
  }

  function startAddAccount() {
    addAccountForm = {
      name: "",
      nickname: "",
      account_type: "",
      classification: "asset",
      initial_balance: "",
      institution_name: "",
    };
    isAddingAccount = true;
  }

  function cancelAddAccount() {
    isAddingAccount = false;
    containerEl?.focus();
  }

  function generateUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  async function saveAddAccount() {
    if (!addAccountForm.name.trim()) {
      error = "Account name is required";
      return;
    }

    try {
      const accountId = generateUUID();
      const now = new Date().toISOString();
      const nameValue = addAccountForm.name.trim().replace(/'/g, "''");
      const nicknameValue = addAccountForm.nickname.trim() || null;
      const typeValue = addAccountForm.account_type.trim() || null;
      const institutionValue = addAccountForm.institution_name.trim() || null;

      // Insert the account
      await executeQuery(
        `INSERT INTO sys_accounts (
          account_id, name, nickname, account_type, currency,
          external_ids, institution_name, created_at, updated_at
        ) VALUES (
          '${accountId}',
          '${nameValue}',
          ${nicknameValue ? `'${nicknameValue.replace(/'/g, "''")}'` : "NULL"},
          ${typeValue ? `'${typeValue.replace(/'/g, "''")}'` : "NULL"},
          'USD',
          '{}',
          ${institutionValue ? `'${institutionValue.replace(/'/g, "''")}'` : "NULL"},
          '${now}',
          '${now}'
        )`,
        { readonly: false }
      );

      // If initial balance provided, create a balance snapshot
      const initialBalance = parseFloat(addAccountForm.initial_balance);
      if (!isNaN(initialBalance) && addAccountForm.initial_balance.trim()) {
        const snapshotId = generateUUID();
        await executeQuery(
          `INSERT INTO sys_balance_snapshots (
            snapshot_id, account_id, balance, snapshot_time, created_at, updated_at
          ) VALUES (
            '${snapshotId}',
            '${accountId}',
            ${initialBalance},
            '${now}',
            '${now}',
            '${now}'
          )`,
          { readonly: false }
        );
      }

      // Update config for classification if not default
      const defaultClass = getDefaultClassification(typeValue);
      if (addAccountForm.classification !== defaultClass) {
        const newConfig = { ...config };
        newConfig.classificationOverrides[accountId] = addAccountForm.classification;
        await saveConfig(newConfig);
      }

      cancelAddAccount();
      await loadAccounts();
    } catch (e) {
      console.error("Failed to add account:", e);
      error = e instanceof Error ? e.message : "Failed to add account";
    }
  }

  async function deleteAccount(account: AccountWithStats) {
    // Only allow deleting accounts with no transactions
    if (account.transaction_count > 0) {
      showToast({
        type: "error",
        title: `Cannot delete account with ${account.transaction_count} transactions`,
      });
      return;
    }

    try {
      // Delete balance snapshots first
      await executeQuery(
        `DELETE FROM sys_balance_snapshots WHERE account_id = '${account.account_id}'`,
        { readonly: false }
      );

      // Delete the account
      await executeQuery(
        `DELETE FROM sys_accounts WHERE account_id = '${account.account_id}'`,
        { readonly: false }
      );

      // Remove from config if present
      const newConfig = { ...config };
      delete newConfig.classificationOverrides[account.account_id];
      newConfig.excludedFromNetWorth = newConfig.excludedFromNetWorth.filter(
        (id) => id !== account.account_id
      );
      await saveConfig(newConfig);

      showToast({
        type: "success",
        title: `Deleted ${account.nickname || account.name}`,
      });

      await loadAccounts();
    } catch (e) {
      console.error("Failed to delete account:", e);
      error = e instanceof Error ? e.message : "Failed to delete account";
    }
  }

  // ============================================================================
  // CSV Import Functions
  // ============================================================================

  function openImportModal(account: AccountWithStats) {
    importAccountId = account.account_id;
    importAccountName = account.nickname || account.name;
    importFilePath = "";
    importFileName = "";
    importHeaders = [];
    importColumnMapping = {};
    importFlipSigns = false;
    importDebitNegative = false;
    importPreview = null;
    importResult = null;
    importError = null;
    isImporting = false;
    showImportModal = true;
    menuOpenForAccount = null;
  }

  function closeImportModal() {
    showImportModal = false;
  }

  async function handleFileSelect() {
    try {
      const path = await pickCsvFile();
      if (!path) return;

      importFilePath = path;
      importFileName = path.split("/").pop() || path;
      importHeaders = await getCsvHeaders(path);
      importColumnMapping = autoDetectColumns(importHeaders);
      importError = null;
    } catch (e) {
      importError = e instanceof Error ? e.message : "Failed to read CSV file";
    }
  }

  function autoDetectColumns(headers: string[]): ImportColumnMapping {
    const mapping: ImportColumnMapping = {};
    const lowerHeaders = headers.map(h => h.toLowerCase());

    // Date patterns
    const datePatterns = ["date", "transaction date", "trans date", "posted"];
    for (let i = 0; i < lowerHeaders.length; i++) {
      if (datePatterns.some(p => lowerHeaders[i].includes(p))) {
        mapping.dateColumn = headers[i];
        break;
      }
    }

    // Amount patterns
    const amountPatterns = ["amount", "total"];
    for (let i = 0; i < lowerHeaders.length; i++) {
      if (amountPatterns.some(p => lowerHeaders[i].includes(p)) && !lowerHeaders[i].includes("debit") && !lowerHeaders[i].includes("credit")) {
        mapping.amountColumn = headers[i];
        break;
      }
    }

    // Always try to detect Debit/Credit columns
    for (let i = 0; i < lowerHeaders.length; i++) {
      if (lowerHeaders[i].includes("debit") || lowerHeaders[i].includes("withdrawal")) {
        mapping.debitColumn = headers[i];
      }
      if (lowerHeaders[i].includes("credit") || lowerHeaders[i].includes("deposit")) {
        mapping.creditColumn = headers[i];
      }
    }

    // Description patterns
    const descPatterns = ["description", "desc", "memo", "payee", "merchant", "details"];
    for (let i = 0; i < lowerHeaders.length; i++) {
      if (descPatterns.some(p => lowerHeaders[i].includes(p))) {
        mapping.descriptionColumn = headers[i];
        break;
      }
    }

    return mapping;
  }

  async function refreshPreview() {
    if (!importFilePath || !importAccountId || !importColumnMapping.dateColumn) {
      return;
    }

    try {
      isLoadingPreview = true;
      importPreview = await importCsvPreview(
        importFilePath,
        importAccountId,
        importColumnMapping,
        importFlipSigns,
        importDebitNegative
      );
      importError = null;
    } catch (e) {
      importPreview = null;
    } finally {
      isLoadingPreview = false;
    }
  }

  function schedulePreviewRefresh() {
    if (previewDebounceTimer) {
      clearTimeout(previewDebounceTimer);
    }
    previewDebounceTimer = setTimeout(() => {
      refreshPreview();
    }, 300);
  }

  // Auto-refresh preview when settings change
  $effect(() => {
    const _ = [
      importColumnMapping.dateColumn,
      importColumnMapping.amountColumn,
      importColumnMapping.descriptionColumn,
      importColumnMapping.debitColumn,
      importColumnMapping.creditColumn,
      importFlipSigns,
      importDebitNegative,
    ];

    if (importFilePath && importAccountId && showImportModal) {
      schedulePreviewRefresh();
    }
  });

  async function handleImportExecute() {
    if (!importFilePath || !importAccountId) return;

    try {
      isImporting = true;
      importError = null;

      const result = await importCsvExecute(
        importFilePath,
        importAccountId,
        importColumnMapping,
        importFlipSigns,
        importDebitNegative
      );

      importResult = result;
      await loadAccounts();

      showToast({
        type: "success",
        title: `Imported ${result.imported} transactions (${result.skipped} skipped)`
      });
    } catch (e) {
      importError = e instanceof Error ? e.message : "Import failed";
    } finally {
      isImporting = false;
    }
  }

  function toggleAccountMenu(accountId: string, e: MouseEvent) {
    e.stopPropagation();
    menuOpenForAccount = menuOpenForAccount === accountId ? null : accountId;
  }

  function closeAccountMenu() {
    menuOpenForAccount = null;
  }

  function formatCurrency(amount: number): string {
    return amount.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "—";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function formatMonth(monthStr: string): string {
    const [year, month] = monthStr.split("-");
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString("en-US", { month: "short" });
  }

  function getDisplayName(account: AccountWithStats): string {
    return account.nickname || account.name;
  }

  function getSubtitle(account: AccountWithStats): string | null {
    if (account.nickname && account.institution_name) {
      return account.institution_name;
    }
    if (account.nickname) {
      return account.name;
    }
    return account.institution_name;
  }

  function getBalanceForDisplay(account: AccountWithStats): number {
    // Use snapshot balance if available, otherwise computed
    return account.balance ?? account.computed_balance;
  }

  // Action bar items
  let actionBarItems = $derived<ActionItem[]>([
    { keys: ["j", "k"], label: "nav", action: () => {} },
    { keys: ["Enter"], label: "view", action: () => currentAccount && showPreview(currentAccount) },
    { keys: ["e"], label: "edit", action: () => currentAccount && startEdit(currentAccount) },
    { keys: ["a"], label: "add", action: startAddAccount },
    { keys: ["d"], label: "delete", action: () => currentAccount && deleteAccount(currentAccount) },
    { keys: ["h", "l"], label: "date", action: () => {} },
    { keys: ["t"], label: "today", action: goToToday, disabled: isToday },
    { keys: ["r"], label: "refresh", action: loadAccounts },
  ]);

  onMount(async () => {
    await loadAccounts();
    // Focus container for keyboard navigation
    containerEl?.focus();

    // Handle action prop from command palette
    if (action === "add") {
      startAddAccount();
    }
  });
</script>

<div class="accounts-view" bind:this={containerEl} tabindex="0" onkeydown={handleKeyDown}>
  <!-- Header -->
  <div class="header">
    <div class="title-row">
      <h1 class="title">Accounts</h1>
      <div class="date-nav">
        <span class="as-of-label">as of</span>
        <button class="nav-btn" onclick={() => cycleDay(-1)} title="Previous day">←</button>
        <input
          type="date"
          class="date-input"
          value={referenceDate.toISOString().split("T")[0]}
          max={new Date().toISOString().split("T")[0]}
          onchange={handleDateChange}
        />
        <button
          class="nav-btn"
          onclick={() => cycleDay(1)}
          disabled={isToday}
          title="Next day"
        >→</button>
        <button class="today-btn" onclick={goToToday} title="Jump to today" disabled={isToday}>Today</button>
      </div>
    </div>
  </div>

  <ActionBar actions={actionBarItems} />

  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  <div class="main-content">
    <!-- Account list -->
    <div class="list-container">
      {#if isLoading}
        <div class="empty-state">Loading...</div>
      {:else if allAccounts.length === 0}
        <div class="empty-state">
          <div class="empty-title">No accounts yet</div>
          <div class="empty-message">
            Add accounts by connecting SimpleFIN or importing transactions from CSV.
          </div>
          <div class="empty-cli">
            <code>$ tl setup</code>
            <code>$ tl setup simplefin</code>
            <code>$ tl import</code>
          </div>
        </div>
      {:else}
        <!-- Net Worth -->
        <div class="net-worth-row">
          <div class="net-worth-label">NET WORTH</div>
          <div class="net-worth-value" class:negative={netWorth < 0}>
            {formatCurrency(netWorth)}
          </div>
          {#if momChange}
            <div class="net-worth-change" class:positive={momChange.change >= 0} class:negative={momChange.change < 0}>
              {momChange.change >= 0 ? "+" : ""}{formatCurrency(momChange.change)} MoM
            </div>
          {/if}
        </div>

        <!-- Assets Section -->
        {#if assetAccounts.length > 0}
          <div class="section">
            <div class="section-header asset-header">
              <div class="section-title">ASSETS</div>
              <div class="section-total">{formatCurrency(totalAssets)}</div>
            </div>
            {#each assetAccounts as account, i}
              {@const globalIndex = i}
              <div
                class="row"
                class:cursor={cursorIndex === globalIndex}
                class:excluded={config.excludedFromNetWorth.includes(account.account_id)}
                data-index={globalIndex}
                onclick={() => handleRowClick(globalIndex)}
                ondblclick={() => handleRowDoubleClick(globalIndex)}
                role="button"
                tabindex="-1"
              >
                <div class="row-name">
                  <span class="account-name">{getDisplayName(account)}</span>
                  {#if getSubtitle(account)}
                    <span class="account-subtitle">{getSubtitle(account)}</span>
                  {/if}
                </div>
                <div class="row-balance">{formatCurrency(getBalanceForDisplay(account))}</div>
                <div class="row-type">{account.account_type || "—"}</div>
                <div class="row-txns">{account.transaction_count.toLocaleString()} txns</div>
                <div class="row-last">{formatDate(account.last_transaction)}</div>
                <RowMenu
                  items={[
                    { label: "Edit", action: () => { startEdit(account); closeAccountMenu(); } },
                    { label: "Import CSV", action: () => openImportModal(account) },
                    { label: "Delete", action: () => { deleteAccount(account); closeAccountMenu(); }, danger: true, disabled: account.transaction_count > 0 },
                  ]}
                  isOpen={menuOpenForAccount === account.account_id}
                  onToggle={(e) => toggleAccountMenu(account.account_id, e)}
                  title="Account actions"
                />
              </div>
            {/each}
          </div>
        {/if}

        <!-- Liabilities Section -->
        {#if liabilityAccounts.length > 0}
          <div class="section">
            <div class="section-header liability-header">
              <div class="section-title">LIABILITIES</div>
              <div class="section-total">{formatCurrency(totalLiabilities)}</div>
            </div>
            {#each liabilityAccounts as account, i}
              {@const globalIndex = assetAccounts.length + i}
              <div
                class="row"
                class:cursor={cursorIndex === globalIndex}
                class:excluded={config.excludedFromNetWorth.includes(account.account_id)}
                data-index={globalIndex}
                onclick={() => handleRowClick(globalIndex)}
                ondblclick={() => handleRowDoubleClick(globalIndex)}
                role="button"
                tabindex="-1"
              >
                <div class="row-name">
                  <span class="account-name">{getDisplayName(account)}</span>
                  {#if getSubtitle(account)}
                    <span class="account-subtitle">{getSubtitle(account)}</span>
                  {/if}
                </div>
                <div class="row-balance liability">{formatCurrency(Math.abs(getBalanceForDisplay(account)))}</div>
                <div class="row-type">{account.account_type || "—"}</div>
                <div class="row-txns">{account.transaction_count.toLocaleString()} txns</div>
                <div class="row-last">{formatDate(account.last_transaction)}</div>
                <RowMenu
                  items={[
                    { label: "Edit", action: () => { startEdit(account); closeAccountMenu(); } },
                    { label: "Import CSV", action: () => openImportModal(account) },
                    { label: "Delete", action: () => { deleteAccount(account); closeAccountMenu(); }, danger: true, disabled: account.transaction_count > 0 },
                  ]}
                  isOpen={menuOpenForAccount === account.account_id}
                  onToggle={(e) => toggleAccountMenu(account.account_id, e)}
                  title="Account actions"
                />
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </div>

    <!-- Sidebar -->
    <div class="sidebar">
      {#if currentAccount}
        <div class="sidebar-section">
          <div class="sidebar-title">Selected</div>
          <div class="detail-name">{getDisplayName(currentAccount)}</div>
          {#if currentAccount.nickname}
            <div class="detail-subtitle">{currentAccount.name}</div>
          {/if}
          {#if currentAccount.institution_name}
            <div class="detail-institution">{currentAccount.institution_name}</div>
          {/if}
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">Details</div>
          <div class="detail-row">
            <span>Type:</span>
            <span class="mono">{currentAccount.account_type || "—"}</span>
          </div>
          <div class="detail-row">
            <span>Classification:</span>
            <span class="mono">{currentAccount.classification}</span>
          </div>
          <div class="detail-row">
            <span>Currency:</span>
            <span class="mono">{currentAccount.currency}</span>
          </div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">Balance {isToday ? "" : `(as of ${referenceDateStr})`}</div>
          <div class="detail-row">
            <span>Amount:</span>
            <span class="mono">{formatCurrency(getBalanceForDisplay(currentAccount))}</span>
          </div>
          {#if balanceTrend.length >= 2}
            {@const current = balanceTrend[balanceTrend.length - 1]}
            {@const previous = balanceTrend[balanceTrend.length - 2]}
            {@const change = current.balance - previous.balance}
            {@const percent = previous.balance !== 0 ? (change / Math.abs(previous.balance)) * 100 : 0}
            <div class="detail-row">
              <span>Prev month:</span>
              <span class="mono">{formatCurrency(previous.balance)}</span>
            </div>
            <div class="detail-row">
              <span>Change:</span>
              <span class="mono" class:positive={change >= 0} class:negative={change < 0}>
                {change >= 0 ? "+" : ""}{formatCurrency(change)} ({percent >= 0 ? "+" : ""}{percent.toFixed(1)}%)
              </span>
            </div>
          {/if}
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">Transactions</div>
          <div class="detail-row">
            <span>Total:</span>
            <span class="mono">{currentAccount.transaction_count.toLocaleString()}</span>
          </div>
          <div class="detail-row">
            <span>First:</span>
            <span class="mono">{currentAccount.first_transaction || "—"}</span>
          </div>
          <div class="detail-row">
            <span>Last:</span>
            <span class="mono">{currentAccount.last_transaction || "—"}</span>
          </div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">Balance on {referenceDay}{referenceDay === 1 ? "st" : referenceDay === 2 ? "nd" : referenceDay === 3 ? "rd" : "th"}</div>
          {#if balanceTrend.length === 0}
            <div class="trend-empty">No snapshots</div>
          {:else}
            {@const maxBalance = Math.max(...balanceTrend.map((t) => Math.abs(t.balance)), 1)}
            {@const sixMonthChange = balanceTrend.length >= 2
              ? balanceTrend[balanceTrend.length - 1].balance - balanceTrend[0].balance
              : 0}
            {@const sixMonthPercent = balanceTrend.length >= 2 && balanceTrend[0].balance !== 0
              ? (sixMonthChange / Math.abs(balanceTrend[0].balance)) * 100
              : 0}
            <div class="trend-chart">
              {#each balanceTrend as point}
                <div class="trend-row">
                  <span class="trend-month">{formatMonth(point.month)}</span>
                  <div class="trend-bar-container">
                    <div
                      class="trend-bar"
                      style="width: {(Math.abs(point.balance) / maxBalance) * 100}%"
                    ></div>
                  </div>
                  <span class="trend-amount">{formatCurrency(point.balance)}</span>
                </div>
              {/each}
            </div>
            {#if balanceTrend.length >= 2}
              <div class="trend-summary" class:positive={sixMonthChange >= 0} class:negative={sixMonthChange < 0}>
                {sixMonthChange >= 0 ? "+" : ""}{formatCurrency(sixMonthChange)} ({sixMonthPercent >= 0 ? "+" : ""}{sixMonthPercent.toFixed(0)}%) over {balanceTrend.length}mo
              </div>
            {/if}
          {/if}
        </div>
      {:else}
        <div class="sidebar-empty">Select an account</div>
      {/if}
    </div>
  </div>

  <Modal
    open={showTransactionPreview && !!previewAccount}
    title={previewAccount?.nickname || previewAccount?.name || ""}
    onclose={closePreview}
    width="500px"
    class="preview-modal"
  >
    {#if previewLoading}
      <div class="modal-loading">Loading...</div>
    {:else if previewTransactions.length === 0}
      <div class="modal-empty">No transactions</div>
    {:else}
      <div class="txn-list">
        {#each previewTransactions as txn}
          <div class="txn-row">
            <span class="txn-date">{txn.transaction_date}</span>
            <span class="txn-desc">{txn.description}</span>
            <span class="txn-amount" class:negative={txn.amount < 0}>{formatCurrency(txn.amount)}</span>
          </div>
        {/each}
      </div>
      <div class="modal-footer">
        <span>{previewTransactions.length} transactions (showing latest 50)</span>
      </div>
    {/if}

    {#snippet actions()}
      <button class="btn secondary" onclick={closePreview}>Close</button>
      <button class="btn secondary" onclick={editFromPreview}>Edit</button>
      <button class="btn primary" onclick={openInQuery}>Open in Query</button>
    {/snippet}
  </Modal>

  <Modal
    open={isEditing && !!editingAccount}
    title="Edit Account"
    onclose={cancelEdit}
  >
    <div class="form">
      <label>
        Account Name (from source)
        <input type="text" value={editingAccount?.name ?? ""} disabled />
      </label>
      <label>
        Nickname (displayed instead of account name)
        <input
          type="text"
          bind:value={editForm.nickname}
          placeholder="e.g., Emergency Fund"
        />
      </label>
      <label>
        Type
        <input
          type="text"
          bind:value={editForm.account_type}
          placeholder="depository, credit, investment, loan, other"
        />
        <span class="form-hint">depository, credit, investment, loan, other</span>
      </label>
      <div class="form-group">
        <span class="form-label">Balance Classification</span>
        <div class="radio-group">
          <label class="radio">
            <input
              type="radio"
              name="classification"
              value="asset"
              bind:group={editForm.classification}
            />
            Asset
            {#if editingAccount && getDefaultClassification(editForm.account_type || editingAccount.account_type) === "asset"}
              <span class="default-badge">default</span>
            {/if}
          </label>
          <label class="radio">
            <input
              type="radio"
              name="classification"
              value="liability"
              bind:group={editForm.classification}
            />
            Liability
            {#if editingAccount && getDefaultClassification(editForm.account_type || editingAccount.account_type) === "liability"}
              <span class="default-badge">default</span>
            {/if}
          </label>
        </div>
      </div>
      <label class="checkbox">
        <input type="checkbox" bind:checked={editForm.excluded_from_net_worth} />
        Exclude from net worth calculation
      </label>
    </div>

    {#snippet actions()}
      <button class="btn secondary" onclick={cancelEdit}>Cancel</button>
      <button class="btn primary" onclick={saveEdit}>Save</button>
    {/snippet}
  </Modal>

  <Modal
    open={isAddingAccount}
    title="Add Manual Account"
    onclose={cancelAddAccount}
  >
    <div class="form">
      <label>
        Account Name *
        <input
          type="text"
          bind:value={addAccountForm.name}
          placeholder="e.g., Home Equity, Cash"
        />
      </label>
      <label>
        Nickname (optional)
        <input
          type="text"
          bind:value={addAccountForm.nickname}
          placeholder="Display name"
        />
      </label>
      <label>
        Institution (optional)
        <input
          type="text"
          bind:value={addAccountForm.institution_name}
          placeholder="e.g., Zillow, Manual"
        />
      </label>
      <label>
        Type
        <input
          type="text"
          bind:value={addAccountForm.account_type}
          placeholder="depository, credit, investment, loan, other"
        />
        <span class="form-hint">depository, credit, investment, loan, other</span>
      </label>
      <div class="form-group">
        <span class="form-label">Balance Classification</span>
        <div class="radio-group">
          <label class="radio">
            <input
              type="radio"
              name="add-classification"
              value="asset"
              bind:group={addAccountForm.classification}
            />
            Asset
          </label>
          <label class="radio">
            <input
              type="radio"
              name="add-classification"
              value="liability"
              bind:group={addAccountForm.classification}
            />
            Liability
          </label>
        </div>
      </div>
      <label>
        Initial Balance (optional)
        <input
          type="text"
          bind:value={addAccountForm.initial_balance}
          placeholder="0.00"
        />
        <span class="form-hint">Current balance as of today</span>
      </label>
    </div>

    {#snippet actions()}
      <button class="btn secondary" onclick={cancelAddAccount}>Cancel</button>
      <button class="btn primary" onclick={saveAddAccount}>Add Account</button>
    {/snippet}
  </Modal>

  <Modal
    open={showImportModal}
    title="Import CSV to {importAccountName}"
    onclose={closeImportModal}
    width="550px"
    class="import-modal"
  >
    <div class="import-body">
      {#if importError}
        <div class="import-error">{importError}</div>
      {/if}

      {#if importResult}
        <!-- Import complete -->
        <div class="import-done">
          <div class="done-icon">✓</div>
          <p class="done-message">Import Complete</p>
          <div class="import-stats">
            <div class="stat">
              <span class="stat-value">{importResult.imported}</span>
              <span class="stat-label">Imported</span>
            </div>
            <div class="stat">
              <span class="stat-value">{importResult.skipped}</span>
              <span class="stat-label">Skipped</span>
            </div>
          </div>
        </div>
      {:else if !importFilePath}
        <!-- Step 1: Select file -->
        <div class="import-step">
          <p class="import-intro">Import transactions from a CSV file exported from your bank.</p>
          <button class="file-select-btn" onclick={handleFileSelect}>
            Select CSV File...
          </button>
        </div>
      {:else}
        <!-- Step 2: Configure and preview -->
        <div class="import-step">
          <div class="import-file-info">
            <span class="file-label">File:</span>
            <span class="file-name">{importFileName}</span>
            <button class="btn-link" onclick={() => { importFilePath = ""; importHeaders = []; importColumnMapping = {}; importPreview = null; }}>Change</button>
          </div>

          <div class="column-mapping">
            <div class="mapping-title">Column Mapping</div>
            <div class="mapping-hint">Auto-detected. Adjust if needed.</div>

            <div class="mapping-row">
              <label>Date Column</label>
              <select bind:value={importColumnMapping.dateColumn}>
                <option value="">-- Select --</option>
                {#each importHeaders as header}
                  <option value={header}>{header}</option>
                {/each}
              </select>
            </div>

            <div class="mapping-row">
              <label>Description Column</label>
              <select bind:value={importColumnMapping.descriptionColumn}>
                <option value="">-- Select --</option>
                {#each importHeaders as header}
                  <option value={header}>{header}</option>
                {/each}
              </select>
            </div>

            <div class="mapping-row">
              <label>Amount Column</label>
              <select bind:value={importColumnMapping.amountColumn}>
                <option value="">-- Select (or use Debit/Credit) --</option>
                {#each importHeaders as header}
                  <option value={header}>{header}</option>
                {/each}
              </select>
            </div>

            <div class="mapping-divider">— OR use separate debit/credit columns —</div>

            <div class="mapping-row">
              <label>Debit Column</label>
              <select bind:value={importColumnMapping.debitColumn}>
                <option value="">-- Select --</option>
                {#each importHeaders as header}
                  <option value={header}>{header}</option>
                {/each}
              </select>
            </div>

            <div class="mapping-row">
              <label>Credit Column</label>
              <select bind:value={importColumnMapping.creditColumn}>
                <option value="">-- Select --</option>
                {#each importHeaders as header}
                  <option value={header}>{header}</option>
                {/each}
              </select>
            </div>
          </div>

          <div class="import-options">
            <label class="checkbox-label">
              <input type="checkbox" bind:checked={importFlipSigns} />
              Flip signs (for credit cards where charges are positive)
            </label>
            <label class="checkbox-label">
              <input type="checkbox" bind:checked={importDebitNegative} />
              Negate debits (if debits show as positive numbers)
            </label>
          </div>

          <!-- Live Preview -->
          {#if importColumnMapping.dateColumn}
            <div class="live-preview-section">
              <div class="live-preview-header">
                <span class="live-preview-title">Live Preview</span>
                {#if isLoadingPreview}
                  <span class="preview-loading">Loading...</span>
                {/if}
              </div>

              <div class="preview-hint">
                <strong>Check the signs:</strong> Spending should be <span class="negative">negative (red)</span>,
                income should be <span class="positive">positive (green)</span>.
                If reversed, toggle "Flip signs" above.
              </div>

              {#if importPreview && importPreview.preview.length > 0}
                <div class="preview-table">
                  <div class="preview-row header">
                    <span class="preview-date">Date</span>
                    <span class="preview-desc">Description</span>
                    <span class="preview-amount">Amount</span>
                  </div>
                  {#each importPreview.preview.slice(0, 5) as txn}
                    <div class="preview-row">
                      <span class="preview-date">{txn.date}</span>
                      <span class="preview-desc">{txn.description || ""}</span>
                      <span class="preview-amount" class:negative={txn.amount < 0}>
                        {txn.amount < 0 ? "-" : ""}${Math.abs(txn.amount).toFixed(2)}
                      </span>
                    </div>
                  {/each}
                </div>
              {:else if !isLoadingPreview}
                <div class="preview-empty">Configure columns to see preview</div>
              {/if}
            </div>
          {/if}
        </div>
      {/if}
    </div>

    {#snippet actions()}
      {#if importResult}
        <button class="btn primary" onclick={closeImportModal}>Done</button>
      {:else if isImporting}
        <button class="btn secondary" disabled>Importing...</button>
      {:else}
        <button class="btn secondary" onclick={closeImportModal}>Cancel</button>
        {#if importFilePath && importPreview && importPreview.preview.length > 0}
          <button class="btn primary" onclick={handleImportExecute}>Import</button>
        {/if}
      {/if}
    {/snippet}
  </Modal>
</div>

<style>
  .accounts-view {
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

  .date-nav {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .as-of-label {
    font-size: 12px;
    color: var(--text-muted);
    margin-right: var(--spacing-xs);
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

  .nav-btn:hover:not(:disabled) {
    background: var(--bg-primary);
  }

  .nav-btn:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .date-input {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    padding: 4px 8px;
    cursor: pointer;
    transition: border-color 0.15s;
  }

  .date-input:hover {
    border-color: var(--accent-primary);
  }

  .date-input:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .today-btn {
    background: var(--accent-primary);
    border: none;
    color: var(--bg-primary);
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    margin-left: var(--spacing-xs);
  }

  .today-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .today-btn:disabled {
    opacity: 0.4;
    cursor: default;
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

  .empty-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-md);
  }

  .empty-message {
    font-size: 13px;
    margin-bottom: var(--spacing-lg);
  }

  .empty-cli {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    padding: var(--spacing-md);
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
    display: inline-flex;
  }

  .empty-cli code {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-primary);
  }

  .section {
    margin-bottom: var(--spacing-sm);
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px var(--spacing-lg);
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-primary);
  }

  .section-header.asset-header {
    border-left: 3px solid var(--accent-success, #22c55e);
  }

  .section-header.asset-header .section-title {
    color: var(--accent-success, #22c55e);
  }

  .section-header.liability-header {
    border-left: 3px solid var(--accent-danger, #ef4444);
  }

  .section-header.liability-header .section-title {
    color: var(--accent-danger, #ef4444);
  }

  .section-title {
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.5px;
  }

  .section-total {
    font-weight: 600;
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

  .row:hover {
    background: var(--bg-secondary);
  }

  .row.cursor {
    background: var(--bg-tertiary);
    border-left: 3px solid var(--text-muted);
    padding-left: calc(var(--spacing-lg) - 3px);
  }

  .row.excluded {
    opacity: 0.5;
  }

  .row-name {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .account-name {
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .account-subtitle {
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .row-balance {
    width: 110px;
    text-align: right;
    font-weight: 600;
    color: var(--text-primary);
    flex-shrink: 0;
  }

  .row-balance.liability {
    color: var(--accent-danger, #ef4444);
  }

  .row-type {
    width: 90px;
    color: var(--text-muted);
    font-size: 11px;
    flex-shrink: 0;
  }

  .row-txns {
    width: 80px;
    text-align: right;
    color: var(--text-muted);
    font-size: 11px;
    flex-shrink: 0;
  }

  .row-last {
    width: 70px;
    text-align: right;
    color: var(--text-muted);
    font-size: 11px;
    flex-shrink: 0;
  }


  .net-worth-row {
    display: flex;
    align-items: center;
    padding: 12px var(--spacing-lg);
    background: var(--bg-secondary);
    border-top: 2px solid var(--border-primary);
    gap: var(--spacing-md);
  }

  .net-worth-label {
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.5px;
    color: var(--text-primary);
  }

  .net-worth-value {
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
    margin-left: auto;
  }

  .net-worth-value.negative {
    color: var(--accent-danger, #ef4444);
  }

  .net-worth-change {
    font-size: 12px;
    font-weight: 500;
  }

  .net-worth-change.positive {
    color: var(--accent-success, #22c55e);
  }

  .net-worth-change.negative {
    color: var(--accent-danger, #ef4444);
  }

  /* Sidebar */
  .sidebar {
    width: 220px;
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
    color: var(--text-muted);
    font-size: 12px;
    font-style: italic;
  }

  .detail-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .detail-subtitle {
    font-size: 11px;
    color: var(--text-muted);
  }

  .detail-institution {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .mono {
    font-family: var(--font-mono);
  }

  .positive {
    color: var(--accent-success, #22c55e) !important;
  }

  .negative {
    color: var(--accent-danger, #ef4444) !important;
  }

  /* Trend chart */
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
    width: 28px;
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
    width: 70px;
    text-align: right;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    flex-shrink: 0;
  }

  .trend-summary {
    margin-top: 8px;
    font-size: 11px;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  /* Form styles (used in modals) */
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

  .form input[type="text"] {
    padding: 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
  }

  .form input[type="text"]:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .form input[type="text"]:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .form-hint {
    font-size: 10px;
    color: var(--text-muted);
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-label {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .radio-group {
    display: flex;
    gap: var(--spacing-lg);
  }

  .radio {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--text-primary);
    cursor: pointer;
  }

  .radio input {
    cursor: pointer;
  }

  .default-badge {
    font-size: 9px;
    padding: 1px 4px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    color: var(--text-muted);
  }

  .checkbox {
    flex-direction: row !important;
    align-items: center !important;
    gap: 8px !important;
    font-size: 13px !important;
    color: var(--text-primary) !important;
    cursor: pointer;
  }

  /* Modal content styles */
  .preview-modal {
    width: 600px;
  }

  .modal-loading,
  .modal-empty {
    padding: var(--spacing-xl);
    text-align: center;
    color: var(--text-muted);
  }

  .txn-list {
    max-height: 400px;
    overflow-y: auto;
    border-bottom: 1px solid var(--border-primary);
  }

  .txn-row {
    display: grid;
    grid-template-columns: 90px 1fr 100px;
    gap: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
    font-size: 12px;
  }

  .txn-row:last-child {
    border-bottom: none;
  }

  .txn-date {
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .txn-desc {
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .txn-amount {
    text-align: right;
    font-family: var(--font-mono);
    color: var(--text-primary);
  }

  .txn-amount.negative {
    color: var(--negative);
  }

  .modal-footer {
    padding: var(--spacing-sm) var(--spacing-lg);
    font-size: 11px;
    color: var(--text-muted);
    background: var(--bg-tertiary);
  }


  /* Import modal */
  .import-modal {
    max-width: 580px;
    width: 90%;
  }

  .import-body {
    max-height: 70vh;
    overflow-y: auto;
  }

  .import-error {
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(255, 100, 100, 0.15);
    color: var(--text-negative);
    border-radius: 4px;
    font-size: 12px;
    margin-bottom: var(--spacing-md);
  }

  .import-step {
    padding: var(--spacing-md) 0;
  }

  .import-intro {
    color: var(--text-muted);
    font-size: 13px;
    margin-bottom: var(--spacing-lg);
    text-align: center;
  }

  .file-select-btn {
    width: 100%;
    padding: var(--spacing-xl) var(--spacing-lg);
    background: var(--bg-tertiary);
    border: 2px dashed var(--border-primary);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 14px;
    cursor: pointer;
    text-align: center;
    transition: all 0.15s ease;
  }

  .file-select-btn:hover {
    background: var(--bg-secondary);
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }

  .import-file-info {
    display: flex;
    align-items: center;
    padding: 10px var(--spacing-md);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    margin-bottom: var(--spacing-lg);
    font-size: 13px;
    gap: var(--spacing-md);
  }

  .file-label {
    color: var(--text-muted);
    font-weight: 500;
  }

  .file-name {
    flex: 1;
    font-family: var(--font-mono);
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .btn-link {
    background: none;
    border: none;
    color: var(--accent-primary);
    font-size: 12px;
    cursor: pointer;
    padding: 0;
    font-weight: 500;
  }

  .btn-link:hover {
    text-decoration: underline;
  }

  .column-mapping {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
  }

  .mapping-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .mapping-hint {
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: var(--spacing-md);
  }

  .mapping-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: var(--spacing-md);
  }

  .mapping-row:last-child {
    margin-bottom: 0;
  }

  .mapping-row label {
    font-size: 12px;
    color: var(--text-secondary);
    font-weight: 500;
  }

  .mapping-row select {
    width: 100%;
    padding: 10px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 13px;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 32px;
  }

  .mapping-row select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .mapping-divider {
    text-align: center;
    font-size: 11px;
    color: var(--text-muted);
    padding: var(--spacing-sm) 0;
    margin: var(--spacing-sm) 0;
    border-top: 1px solid var(--border-primary);
    border-bottom: 1px solid var(--border-primary);
  }

  .import-options {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 12px;
    color: var(--text-primary);
    cursor: pointer;
  }

  .checkbox-label input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--accent-primary);
    cursor: pointer;
  }

  .live-preview-section {
    margin-top: var(--spacing-lg);
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--border-primary);
  }

  .live-preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--spacing-sm);
  }

  .live-preview-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .preview-loading {
    font-size: 11px;
    color: var(--text-muted);
    font-style: italic;
  }

  .preview-hint {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: var(--spacing-md);
    line-height: 1.5;
  }

  .preview-hint .negative {
    color: var(--text-negative, #ef4444);
    font-weight: 600;
  }

  .preview-hint .positive {
    color: var(--text-positive, #22c55e);
    font-weight: 600;
  }

  .preview-table {
    width: 100%;
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    overflow: hidden;
    font-size: 12px;
    max-height: 200px;
    overflow-y: auto;
  }

  .preview-row {
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--border-primary);
  }

  .preview-row:last-child {
    border-bottom: none;
  }

  .preview-row.header {
    background: var(--bg-tertiary);
    font-weight: 600;
    color: var(--text-muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .preview-row:not(.header):nth-child(odd) {
    background: var(--bg-secondary);
  }

  .preview-date {
    width: 90px;
    flex-shrink: 0;
    padding: 8px 10px;
    font-family: var(--font-mono);
  }

  .preview-desc {
    flex: 1;
    min-width: 0;
    padding: 8px 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .preview-amount {
    width: 90px;
    flex-shrink: 0;
    padding: 8px 10px;
    text-align: right;
    font-family: var(--font-mono);
    font-weight: 500;
  }

  .preview-amount.negative {
    color: var(--text-negative, #ef4444);
  }

  .preview-amount:not(.negative) {
    color: var(--text-positive, #22c55e);
  }

  .preview-empty {
    text-align: center;
    padding: var(--spacing-lg);
    color: var(--text-muted);
    font-style: italic;
    font-size: 12px;
  }

  .import-done {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--spacing-xl) var(--spacing-lg);
    gap: var(--spacing-md);
  }

  .done-icon {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--text-positive, #22c55e);
    color: white;
    border-radius: 50%;
    font-size: 28px;
    font-weight: bold;
  }

  .done-message {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .import-stats {
    display: flex;
    gap: var(--spacing-xl);
    margin-top: var(--spacing-md);
  }

  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    min-width: 80px;
  }

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--accent-primary);
    font-family: var(--font-mono);
  }

  .stat-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    text-align: center;
  }
</style>
