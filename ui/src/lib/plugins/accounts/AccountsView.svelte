<script lang="ts">
  import { onMount } from "svelte";
  import { executeQuery, registry } from "../../sdk";
  import { invoke } from "@tauri-apps/api/core";
  import type {
    AccountWithStats,
    BalanceClassification,
    BalanceTrendPoint,
    AccountsConfig,
  } from "./types";
  import { getDefaultClassification } from "./types";

  const PLUGIN_ID = "accounts";
  const CONFIG_FILE = "accounts_config.json";

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

  async function loadConfig(): Promise<AccountsConfig> {
    try {
      const content = await invoke<string>("read_plugin_config", {
        pluginId: PLUGIN_ID,
        filename: CONFIG_FILE,
      });
      if (content === "null" || !content) {
        return { classificationOverrides: {}, excludedFromNetWorth: [] };
      }
      return JSON.parse(content);
    } catch (e) {
      return { classificationOverrides: {}, excludedFromNetWorth: [] };
    }
  }

  async function saveConfig(newConfig: AccountsConfig): Promise<void> {
    await invoke("write_plugin_config", {
      pluginId: PLUGIN_ID,
      filename: CONFIG_FILE,
      content: JSON.stringify(newConfig, null, 2),
    });
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
          transaction_count: row[9] as number,
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
    if (isEditing || showTransactionPreview) return;

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
      case "n":
        e.preventDefault();
        if (currentAccount) startEdit(currentAccount);
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

  onMount(async () => {
    await loadAccounts();
    // Focus container for keyboard navigation
    containerEl?.focus();
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

  <!-- Help bar -->
  <div class="help-bar">
    <span><kbd>j</kbd><kbd>k</kbd> nav</span>
    <span><kbd>Enter</kbd> transactions</span>
    <span><kbd>e</kbd> edit</span>
    <span><kbd>h</kbd><kbd>l</kbd> date</span>
    <span><kbd>t</kbd> today</span>
    <span><kbd>r</kbd> refresh</span>
  </div>

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

  <!-- Transaction Preview Modal -->
  {#if showTransactionPreview && previewAccount}
    <div
      class="modal-overlay"
      onclick={closePreview}
      onkeydown={(e) => e.key === "Escape" && closePreview()}
      role="dialog"
      tabindex="-1"
    >
      <div class="modal preview-modal" onclick={(e) => e.stopPropagation()} role="document">
        <div class="modal-header">
          <span class="modal-title">{previewAccount.nickname || previewAccount.name}</span>
          <button class="close-btn" onclick={closePreview}>×</button>
        </div>
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
        <div class="modal-actions">
          <button class="btn secondary" onclick={closePreview}>Close</button>
          <button class="btn primary" onclick={openInQuery}>Open in Query →</button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Edit Modal -->
  {#if isEditing && editingAccount}
    <div
      class="modal-overlay"
      onclick={cancelEdit}
      onkeydown={(e) => e.key === "Escape" && cancelEdit()}
      role="dialog"
      tabindex="-1"
    >
      <div class="modal" onclick={(e) => e.stopPropagation()} role="document">
        <div class="modal-header">
          <span class="modal-title">Edit Account</span>
          <button class="close-btn" onclick={cancelEdit}>×</button>
        </div>
        <div class="form">
          <label>
            Account Name (from source)
            <input type="text" value={editingAccount.name} disabled />
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
                {#if getDefaultClassification(editForm.account_type || editingAccount.account_type) === "asset"}
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
                {#if getDefaultClassification(editForm.account_type || editingAccount.account_type) === "liability"}
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
        <div class="modal-actions">
          <button class="btn secondary" onclick={cancelEdit}>Cancel</button>
          <button class="btn primary" onclick={saveEdit}>Save</button>
        </div>
      </div>
    </div>
  {/if}
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

  /* Modal */
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

  .btn:hover {
    opacity: 0.9;
  }

  /* Transaction Preview Modal */
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
</style>
