<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    executeQuery,
    registry,
    showToast,
    runBackfill,
  } from "../../sdk";
  import { Modal, RowMenu, type RowMenuItem, Icon, Sparkline, LineAreaChart, type DataPoint } from "../../shared";
  import type {
    AccountWithStats,
    BalanceClassification,
    BalanceTrendPoint,
    AccountsConfig,
  } from "./types";
  import { getDefaultClassification } from "./types";
  import CsvImportModal from "./CsvImportModal.svelte";
  import SetBalanceModal from "./SetBalanceModal.svelte";

  // Props (passed from openView)
  interface Props {
    action?: "add";
  }
  let { action }: Props = $props();


  // State
  let accounts = $state<AccountWithStats[]>([]);
  let isLoading = $state(true);
  let error = $state<string | null>(null);
  let config = $state<AccountsConfig>({
    classificationOverrides: {},
    excludedFromNetWorth: [],
  });

  // Per-account sparkline and monthly change data
  let accountSparklines = $state<Map<string, number[]>>(new Map());
  let accountMonthlyChanges = $state<Map<string, { change: number; percent: number }>>(new Map());

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

  // Balance trend for selected account (shown in detail panel)
  let balanceTrend = $state<BalanceTrendPoint[]>([]);

  // All balance snapshots for selected account (for detailed chart)
  let allBalanceSnapshots = $state<{ date: string; balance: number }[]>([]);

  // Net worth trend for MoM calculation (aggregates all accounts)
  let netWorthTrend = $state<{ month: string; netWorth: number }[]>([]);

  // Daily net worth data for chart
  let dailyNetWorth = $state<{ date: string; netWorth: number }[]>([]);

  // Net worth chart time range
  type TimeRange = "30d" | "90d" | "6m" | "1y" | "ytd" | "all";
  let chartTimeRange = $state<TimeRange>("90d");

  const timeRangeOptions: { value: TimeRange; label: string }[] = [
    { value: "30d", label: "30D" },
    { value: "90d", label: "90D" },
    { value: "6m", label: "6M" },
    { value: "1y", label: "1Y" },
    { value: "ytd", label: "YTD" },
    { value: "all", label: "All" },
  ];

  // Net worth section expanded state (default to expanded for visibility)
  let netWorthExpanded = $state(true);

  // Detail panel state (always visible in split view when account selected)
  let showDetailPanel = $state(true);

  // Snapshot history in detail panel
  let detailSnapshots = $state<{
    snapshot_id: string;
    balance: number;
    snapshot_time: string;
    source: string;
  }[]>([]);
  let detailSnapshotsLoading = $state(false);

  // Edit modal
  let isEditing = $state(false);
  let editingAccount = $state<AccountWithStats | null>(null);
  let editForm = $state({
    name: "",
    nickname: "",
    account_type: "",
    classification: "asset" as BalanceClassification,
    excluded_from_net_worth: false,
    institution_name: "",
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

  // Set Balance modal
  let showSetBalanceModal = $state(false);
  let setBalanceAccountId = $state("");
  let setBalanceAccountName = $state("");
  let setBalanceCurrentBalance = $state<number | null>(null);
  let setBalanceCurrentDate = $state<string | null>(null);

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

  // Sparkline data (just values for compact display - use daily data)
  let sparklineData = $derived(dailyNetWorth.map((t) => t.netWorth));

  // Chart data for LineAreaChart (daily data, show ~10 labels)
  let netWorthChartData = $derived<DataPoint[]>(
    dailyNetWorth.map((t, i) => {
      // Show label every ~10 days for readability
      const showLabel = i === 0 || i === dailyNetWorth.length - 1 || i % Math.max(1, Math.floor(dailyNetWorth.length / 5)) === 0;
      return {
        label: showLabel ? formatDateShort(t.date) : "",
        value: t.netWorth,
      };
    })
  );

  // Period change calculation (based on daily data range)
  let periodChange = $derived.by(() => {
    if (dailyNetWorth.length < 2) return null;
    const first = dailyNetWorth[0]?.netWorth ?? 0;
    const last = dailyNetWorth[dailyNetWorth.length - 1]?.netWorth ?? 0;
    const change = last - first;
    const percent = first !== 0 ? (change / Math.abs(first)) * 100 : 0;
    const days = dailyNetWorth.length;
    return { change, percent, days };
  });

  // Balance trend chart data for detail panel (using all snapshots)
  let balanceTrendChartData = $derived.by(() => {
    if (allBalanceSnapshots.length === 0) return [] as DataPoint[];

    // Show labels for first, last, and a few points in between
    const labelInterval = Math.max(1, Math.floor(allBalanceSnapshots.length / 4));

    return allBalanceSnapshots.map((s, i) => ({
      label: (i === 0 || i === allBalanceSnapshots.length - 1 || i % labelInterval === 0)
        ? formatDateShort(s.date)
        : "",
      value: s.balance,
    }));
  });

  function formatDateShort(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  /**
   * Load account overrides from DuckDB
   */
  async function loadConfig(): Promise<AccountsConfig> {
    try {
      const result = await executeQuery(`
        SELECT account_id, classification_override, exclude_from_net_worth
        FROM sys_plugin_accounts_overrides
      `);

      const classificationOverrides: Record<string, BalanceClassification> = {};
      const excludedFromNetWorth: string[] = [];

      for (const row of result.rows) {
        const accountId = row[0] as string;
        const classificationOverride = row[1] as BalanceClassification | null;
        const excludeFromNetWorth = row[2] as boolean;

        if (classificationOverride) {
          classificationOverrides[accountId] = classificationOverride;
        }
        if (excludeFromNetWorth) {
          excludedFromNetWorth.push(accountId);
        }
      }

      return { classificationOverrides, excludedFromNetWorth };
    } catch (e) {
      // Table might not exist yet - return defaults
      console.warn("Failed to load account overrides:", e);
      return { classificationOverrides: {}, excludedFromNetWorth: [] };
    }
  }

  /**
   * Save an account override to DuckDB
   */
  async function saveAccountOverride(
    accountId: string,
    classificationOverride: BalanceClassification | null,
    excludeFromNetWorth: boolean
  ): Promise<void> {
    const classValue = classificationOverride ? `'${classificationOverride}'` : "NULL";

    await executeQuery(
      `
      INSERT INTO sys_plugin_accounts_overrides
        (account_id, classification_override, exclude_from_net_worth, updated_at)
      VALUES
        ('${accountId}', ${classValue}, ${excludeFromNetWorth}, now())
      ON CONFLICT (account_id) DO UPDATE SET
        classification_override = EXCLUDED.classification_override,
        exclude_from_net_worth = EXCLUDED.exclude_from_net_worth,
        updated_at = now()
      `,
      { readonly: false }
    );
  }

  /**
   * Delete an account override from DuckDB
   */
  async function deleteAccountOverride(accountId: string): Promise<void> {
    await executeQuery(
      `DELETE FROM sys_plugin_accounts_overrides WHERE account_id = '${accountId}'`,
      { readonly: false }
    );
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
        ),
        computed_balances AS (
          SELECT
            account_id,
            SUM(amount) as computed_balance
          FROM transactions
          WHERE transaction_date <= '${refDateStr.split(' ')[0]}'
          GROUP BY account_id
        )
        SELECT
          a.account_id,
          a.name,
          a.nickname,
          a.account_type,
          a.currency,
          sao.balance,
          a.institution_name,
          a.created_at,
          a.updated_at,
          COALESCE(s.transaction_count, 0) as transaction_count,
          s.first_transaction,
          s.last_transaction,
          COALESCE(cb.computed_balance, 0) as computed_balance,
          sao.snapshot_time as balance_as_of,
          a.external_ids
        FROM accounts a
        LEFT JOIN snapshots_as_of sao ON a.account_id = sao.account_id AND sao.rn = 1
        LEFT JOIN account_stats s ON a.account_id = s.account_id
        LEFT JOIN computed_balances cb ON a.account_id = cb.account_id
        ORDER BY
          CASE WHEN sao.balance IS NOT NULL THEN ABS(sao.balance) ELSE COALESCE(ABS(cb.computed_balance), 0) END DESC,
          a.name
      `);

      accounts = result.rows.map((row) => {
        const accountType = row[3] as string | null;
        const accountId = row[0] as string;

        // Check for classification override
        const classificationOverride = config.classificationOverrides[accountId];
        const classification = classificationOverride ?? getDefaultClassification(accountType);

        // Check if manual account (no external IDs)
        const externalIds = row[14] as Record<string, string> | null;
        const isManual = !externalIds || Object.keys(externalIds).length === 0;

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
          computed_balance: row[12] as number,
          balance_as_of: row[13] as string | null,
          classification,
          external_ids: externalIds ?? {},
          isManual,
        };
      });

      // Load net worth trends and per-account data
      await Promise.all([
        loadNetWorthTrend(),
        loadDailyNetWorth(),
        loadAccountSparklines(),
      ]);

      // Ensure cursor is valid
      if (cursorIndex >= accounts.length) {
        cursorIndex = Math.max(0, accounts.length - 1);
      }
    } catch (e) {
      console.error("Failed to load accounts:", e);
      error = e instanceof Error ? e.message : "Failed to load accounts";
    } finally {
      isLoading = false;
    }
  }

  /**
   * Load sparkline data and monthly change for all accounts
   */
  async function loadAccountSparklines() {
    const newSparklines = new Map<string, number[]>();
    const newChanges = new Map<string, { change: number; percent: number }>();

    // Get last 6 months of balance data for each account
    const day = referenceDay;

    for (const account of accounts) {
      try {
        const result = await executeQuery(`
          SELECT
            account_id,
            balance,
            snapshot_time
          FROM balance_snapshots
          WHERE account_id = '${account.account_id}'
          ORDER BY snapshot_time DESC
        `);

        if (result.rows.length === 0) {
          continue;
        }

        // Group snapshots by month
        const snapshotsByMonth = new Map<string, { balance: number; day: number }[]>();
        for (const row of result.rows) {
          const snapshotTime = new Date(row[2] as string);
          const monthKey = `${snapshotTime.getFullYear()}-${String(snapshotTime.getMonth() + 1).padStart(2, "0")}`;
          const snapshotDay = snapshotTime.getDate();
          if (!snapshotsByMonth.has(monthKey)) {
            snapshotsByMonth.set(monthKey, []);
          }
          snapshotsByMonth.get(monthKey)!.push({ balance: row[1] as number, day: snapshotDay });
        }

        // Get last 6 months of data
        const sparklineValues: number[] = [];
        for (let i = 5; i >= 0; i--) {
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
            sparklineValues.push(closest.balance);
          }
        }

        if (sparklineValues.length > 0) {
          newSparklines.set(account.account_id, sparklineValues);

          // Calculate monthly change
          if (sparklineValues.length >= 2) {
            const current = sparklineValues[sparklineValues.length - 1];
            const previous = sparklineValues[sparklineValues.length - 2];
            const change = current - previous;
            const percent = previous !== 0 ? (change / Math.abs(previous)) * 100 : 0;
            newChanges.set(account.account_id, { change, percent });
          }
        }
      } catch (e) {
        console.error(`Failed to load sparkline for ${account.account_id}:`, e);
      }
    }

    accountSparklines = newSparklines;
    accountMonthlyChanges = newChanges;
  }

  /**
   * Load balance trend for a specific account (for detail panel)
   */
  async function loadBalanceTrend(accountId: string) {
    const day = referenceDay;
    const trends: BalanceTrendPoint[] = [];

    const result = await executeQuery(`
      SELECT
        account_id,
        balance,
        snapshot_time
      FROM balance_snapshots
      WHERE account_id = '${accountId}'
      ORDER BY snapshot_time ASC
    `);

    if (result.rows.length === 0) {
      balanceTrend = [];
      allBalanceSnapshots = [];
      return;
    }

    // Store all snapshots for the detailed chart
    allBalanceSnapshots = result.rows.map((row) => ({
      date: (row[2] as string).split("T")[0].split(" ")[0],
      balance: row[1] as number,
    }));

    // Group snapshots by month and find the one closest to our reference day (for MoM calc)
    const snapshotsByMonth = new Map<string, { balance: number; snapshot_time: string; day: number }[]>();

    for (const row of result.rows) {
      const snapshotTime = new Date(row[2] as string);
      const monthKey = `${snapshotTime.getFullYear()}-${String(snapshotTime.getMonth() + 1).padStart(2, "0")}`;
      const snapshotDay = snapshotTime.getDate();

      if (!snapshotsByMonth.has(monthKey)) {
        snapshotsByMonth.set(monthKey, []);
      }
      snapshotsByMonth.get(monthKey)!.push({
        balance: row[1] as number,
        snapshot_time: row[2] as string,
        day: snapshotDay,
      });
    }

    // For each of the last 6 months relative to reference date, find the snapshot closest to our reference day
    for (let i = 5; i >= 0; i--) {
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

        trends.push({
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

    // Build the 6 target months (from referenceDate going back)
    const targetMonths: { monthKey: string; targetDay: number; endOfMonth: Date }[] = [];
    for (let i = 5; i >= 0; i--) {
      const targetDate = new Date(referenceDate.getFullYear(), referenceDate.getMonth() - i, 1);
      const monthKey = `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, "0")}`;
      const daysInMonth = new Date(targetDate.getFullYear(), targetDate.getMonth() + 1, 0).getDate();
      const targetDay = Math.min(day, daysInMonth);
      // End of the target day in that month
      const endOfMonth = new Date(targetDate.getFullYear(), targetDate.getMonth(), targetDay, 23, 59, 59);
      targetMonths.push({ monthKey, targetDay, endOfMonth });
    }

    // For each target month, get the most recent balance for each account as of that date
    const trends: { month: string; netWorth: number }[] = [];

    for (const { monthKey, targetDay, endOfMonth } of targetMonths) {
      const endOfMonthStr = `${endOfMonth.getFullYear()}-${String(endOfMonth.getMonth() + 1).padStart(2, "0")}-${String(endOfMonth.getDate()).padStart(2, "0")} 23:59:59`;

      // Get the most recent snapshot for each account as of the target date
      const result = await executeQuery(`
        WITH ranked AS (
          SELECT
            bs.account_id,
            bs.balance,
            bs.snapshot_time,
            a.account_type,
            ROW_NUMBER() OVER (PARTITION BY bs.account_id ORDER BY bs.snapshot_time DESC) as rn
          FROM balance_snapshots bs
          JOIN accounts a ON bs.account_id = a.account_id
          WHERE bs.snapshot_time <= '${endOfMonthStr}'
        )
        SELECT account_id, balance, snapshot_time, account_type
        FROM ranked
        WHERE rn = 1
      `);

      if (result.rows.length === 0) {
        continue;
      }

      let monthNetWorth = 0;

      for (const row of result.rows) {
        const accountId = row[0] as string;
        if (excludedIds.includes(accountId)) continue;

        const balance = row[1] as number;
        const accountType = row[3] as string | null;

        // Check classification (use config override or default)
        const classification =
          config.classificationOverrides[accountId] ??
          getDefaultClassification(accountType);

        if (classification === "liability") {
          monthNetWorth -= Math.abs(balance);
        } else {
          monthNetWorth += balance;
        }
      }

      trends.push({ month: monthKey, netWorth: monthNetWorth });
    }

    netWorthTrend = trends;
  }

  /**
   * Calculate number of days for the selected time range
   */
  function getTimeRangeDays(range: TimeRange): number | null {
    const now = referenceDate;
    switch (range) {
      case "30d":
        return 30;
      case "90d":
        return 90;
      case "6m":
        return 180;
      case "1y":
        return 365;
      case "ytd": {
        const startOfYear = new Date(now.getFullYear(), 0, 1);
        return Math.ceil((now.getTime() - startOfYear.getTime()) / (1000 * 60 * 60 * 24)) + 1;
      }
      case "all":
        return null; // Will be determined by earliest data
    }
  }

  /**
   * Load daily net worth data for the chart based on selected time range
   */
  async function loadDailyNetWorth() {
    const excludedIds = config.excludedFromNetWorth;
    let days = getTimeRangeDays(chartTimeRange);

    // For "all", get the earliest snapshot date first
    if (days === null) {
      const minResult = await executeQuery(`
        SELECT MIN(snapshot_time) as min_date FROM balance_snapshots
      `);
      if (minResult.rows.length > 0 && minResult.rows[0][0]) {
        const minDate = minResult.rows[0][0] as string;
        const minDateObj = new Date(minDate.split(' ')[0]);
        days = Math.ceil((referenceDate.getTime() - minDateObj.getTime()) / (1000 * 60 * 60 * 24)) + 1;
        days = Math.max(days, 1);
      } else {
        days = 90; // Fallback
      }
    }

    // Build list of dates
    const dates: string[] = [];
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(referenceDate);
      date.setDate(date.getDate() - i);
      const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
      dates.push(dateStr);
    }

    const startDate = dates[0];
    const endDate = dates[dates.length - 1] + " 23:59:59";

    // FIRST: Get the most recent snapshot for each account BEFORE the start date
    // This initializes balances that should carry forward into our date range
    const initialBalancesResult = await executeQuery(`
      WITH ranked AS (
        SELECT
          bs.account_id,
          bs.balance,
          bs.snapshot_time,
          a.account_type,
          ROW_NUMBER() OVER (PARTITION BY bs.account_id ORDER BY bs.snapshot_time DESC) as rn
        FROM balance_snapshots bs
        JOIN accounts a ON bs.account_id = a.account_id
        WHERE bs.snapshot_time < '${startDate}'
      )
      SELECT account_id, balance, account_type
      FROM ranked
      WHERE rn = 1
    `);

    // Initialize currentBalances with snapshots from before the date range
    const currentBalances = new Map<string, { balance: number; accountType: string | null }>();
    for (const row of initialBalancesResult.rows) {
      const accountId = row[0] as string;
      const balance = row[1] as number;
      const accountType = row[2] as string | null;
      currentBalances.set(accountId, { balance, accountType });
    }

    // THEN: Get all snapshots within the date range
    const result = await executeQuery(`
      SELECT
        bs.account_id,
        bs.balance,
        DATE_TRUNC('day', bs.snapshot_time) as snapshot_date,
        a.account_type
      FROM balance_snapshots bs
      JOIN accounts a ON bs.account_id = a.account_id
      WHERE bs.snapshot_time >= '${startDate}'
        AND bs.snapshot_time <= '${endDate}'
      ORDER BY bs.snapshot_time
    `);

    // Group snapshots by date and account, keeping the latest snapshot per day per account
    const snapshotsByDateAccount = new Map<string, Map<string, { balance: number; accountType: string | null }>>();

    for (const row of result.rows) {
      const accountId = row[0] as string;
      const balance = row[1] as number;
      // DATE_TRUNC returns a string like "2024-12-10 00:00:00" from DuckDB
      const rawDate = row[2] as string | Date;
      const snapshotDate = typeof rawDate === 'string'
        ? rawDate.split(' ')[0]  // "2024-12-10 00:00:00" -> "2024-12-10"
        : rawDate.toISOString().split("T")[0];
      const accountType = row[3] as string | null;

      if (!snapshotsByDateAccount.has(snapshotDate)) {
        snapshotsByDateAccount.set(snapshotDate, new Map());
      }
      // Later snapshot overwrites earlier one for same account on same day
      snapshotsByDateAccount.get(snapshotDate)!.set(accountId, { balance, accountType });
    }

    // Build daily net worth by carrying forward balances
    const daily: { date: string; netWorth: number }[] = [];

    for (const dateStr of dates) {
      // Update balances for this date
      const daySnapshots = snapshotsByDateAccount.get(dateStr);
      if (daySnapshots) {
        for (const [accountId, data] of daySnapshots) {
          currentBalances.set(accountId, data);
        }
      }

      // Calculate net worth for this date
      let netWorth = 0;
      for (const [accountId, data] of currentBalances) {
        if (excludedIds.includes(accountId)) continue;

        const classification =
          config.classificationOverrides[accountId] ??
          getDefaultClassification(data.accountType);

        if (classification === "liability") {
          netWorth -= Math.abs(data.balance);
        } else {
          netWorth += data.balance;
        }
      }

      // Only include days where we have at least some data
      if (currentBalances.size > 0) {
        daily.push({ date: dateStr, netWorth });
      }
    }

    dailyNetWorth = daily;
  }

  /**
   * Load snapshot history for detail panel
   */
  async function loadDetailSnapshots(accountId: string) {
    detailSnapshotsLoading = true;
    detailSnapshots = [];

    try {
      const result = await executeQuery(`
        SELECT
          snapshot_id,
          balance,
          snapshot_time,
          source
        FROM sys_balance_snapshots
        WHERE account_id = '${accountId}'
        ORDER BY snapshot_time DESC
        LIMIT 50
      `);

      detailSnapshots = result.rows.map((row) => ({
        snapshot_id: row[0] as string,
        balance: row[1] as number,
        snapshot_time: row[2] as string,
        source: row[3] as string,
      }));
    } catch (e) {
      console.error("Failed to load snapshots:", e);
      detailSnapshots = [];
    } finally {
      detailSnapshotsLoading = false;
    }
  }

  // Effect: load trend and snapshots when account changes
  $effect(() => {
    if (currentAccount && !isLoading) {
      loadBalanceTrend(currentAccount.account_id);
      loadDetailSnapshots(currentAccount.account_id);
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

  // Effect: reload daily net worth when time range changes
  let previousTimeRange: TimeRange | null = null;
  $effect(() => {
    if (previousTimeRange !== null && previousTimeRange !== chartTimeRange && !isLoading) {
      loadDailyNetWorth();
    }
    previousTimeRange = chartTimeRange;
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
      case "s":
        e.preventDefault();
        if (currentAccount) openSetBalanceModal(currentAccount);
        break;
      case "i":
        e.preventDefault();
        if (currentAccount) openImportModal(currentAccount);
        break;
      case "Escape":
        e.preventDefault();
        showDetailPanel = false;
        break;
      case "Tab":
        e.preventDefault();
        showDetailPanel = !showDetailPanel;
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
    showDetailPanel = true;
    containerEl?.focus();
  }

  function handleRowDoubleClick(index: number) {
    const account = allAccounts[index];
    if (account) {
      showPreview(account);
    }
  }

  async function deleteSnapshot(snapshotId: string) {
    try {
      await executeQuery(
        `DELETE FROM sys_balance_snapshots WHERE snapshot_id = '${snapshotId}'`,
        { readonly: false }
      );
      // Remove from local state
      detailSnapshots = detailSnapshots.filter((s) => s.snapshot_id !== snapshotId);
      // Reload accounts to update balance display
      await loadAccounts();
      showToast({ type: "success", title: "Snapshot deleted" });
    } catch (e) {
      console.error("Failed to delete snapshot:", e);
      showToast({ type: "error", title: "Failed to delete snapshot" });
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
      name: account.name,
      nickname: account.nickname || "",
      account_type: account.account_type || "",
      classification: account.classification,
      excluded_from_net_worth: config.excludedFromNetWorth.includes(account.account_id),
      institution_name: account.institution_name || "",
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
      // Update account fields in database
      const nicknameValue = editForm.nickname.trim() || null;
      const typeValue = editForm.account_type.trim() || null;

      // Build SET clause - name and institution_name are only editable for manual accounts
      let setClause = `
        nickname = ${nicknameValue ? `'${nicknameValue.replace(/'/g, "''")}'` : "NULL"},
        account_type = ${typeValue ? `'${typeValue.replace(/'/g, "''")}'` : "NULL"},
        updated_at = CURRENT_TIMESTAMP`;

      // For manual accounts, also allow editing name and institution
      if (editingAccount.isManual) {
        const nameValue = editForm.name.trim();
        const institutionValue = editForm.institution_name.trim() || null;

        if (!nameValue) {
          error = "Account name is required";
          return;
        }

        setClause = `
          name = '${nameValue.replace(/'/g, "''")}',
          institution_name = ${institutionValue ? `'${institutionValue.replace(/'/g, "''")}'` : "NULL"},` + setClause;
      }

      await executeQuery(
        `UPDATE sys_accounts SET ${setClause}
        WHERE account_id = '${editingAccount.account_id}'`,
        { readonly: false }
      );

      // Save classification override and exclusion to DuckDB
      const defaultClass = getDefaultClassification(typeValue);
      const classificationOverride = editForm.classification !== defaultClass ? editForm.classification : null;
      const hasOverride = classificationOverride !== null || editForm.excluded_from_net_worth;

      if (hasOverride) {
        await saveAccountOverride(
          editingAccount.account_id,
          classificationOverride,
          editForm.excluded_from_net_worth
        );
      } else {
        // No override needed - remove any existing row
        await deleteAccountOverride(editingAccount.account_id);
      }

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

      // Save classification override if not default
      const defaultClass = getDefaultClassification(typeValue);
      if (addAccountForm.classification !== defaultClass) {
        await saveAccountOverride(accountId, addAccountForm.classification, false);
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

      // Remove account override if present
      await deleteAccountOverride(account.account_id);

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
    showImportModal = true;
    menuOpenForAccount = null;
  }

  function closeImportModal() {
    showImportModal = false;
  }

  async function handleImportSuccess() {
    await loadAccounts();
  }

  // Set Balance modal functions
  function openSetBalanceModal(account: AccountWithStats) {
    setBalanceAccountId = account.account_id;
    setBalanceAccountName = account.nickname || account.name;
    setBalanceCurrentBalance = account.balance;
    setBalanceCurrentDate = account.balance_as_of?.split("T")[0] ?? null;
    showSetBalanceModal = true;
    menuOpenForAccount = null;
  }

  function closeSetBalanceModal() {
    showSetBalanceModal = false;
  }

  async function handleSetBalanceSave(balance: number, date: string, shouldBackfill: boolean) {
    // Balance is already saved by the modal
    if (shouldBackfill) {
      showToast({ type: "info", title: "Calculating historical balances..." });
      try {
        await runBackfill(setBalanceAccountId);
        showToast({ type: "success", title: "Historical balances calculated" });
      } catch (e) {
        console.error("Backfill failed:", e);
        showToast({ type: "error", title: "Failed to calculate historical balances" });
      }
    } else {
      showToast({ type: "success", title: "Balance saved" });
    }
    showSetBalanceModal = false;
    await loadAccounts();
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

  function formatCurrencyCompact(amount: number): string {
    const absAmount = Math.abs(amount);
    if (absAmount >= 1000000) {
      return (amount / 1000000).toFixed(1) + "M";
    } else if (absAmount >= 1000) {
      return (amount / 1000).toFixed(1) + "K";
    }
    return formatCurrency(amount);
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "";
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
    if (account.institution_name) {
      return account.institution_name;
    }
    if (account.nickname) {
      return account.name;
    }
    return null;
  }

  function getBalanceForDisplay(account: AccountWithStats): number {
    // Use snapshot balance if available, otherwise computed
    return account.balance ?? account.computed_balance;
  }


  // Subscribe to global refresh events
  let unsubscribeRefresh: (() => void) | null = null;

  onMount(async () => {
    await loadAccounts();
    // Focus container for keyboard navigation
    containerEl?.focus();

    // Handle action prop from command palette
    if (action === "add") {
      startAddAccount();
    }

    // Listen for data refresh events (e.g., demo mode toggle)
    unsubscribeRefresh = registry.on("data:refresh", () => {
      loadAccounts();
    });
  });

  onDestroy(() => {
    unsubscribeRefresh?.();
  });
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="accounts-view" bind:this={containerEl} tabindex="0" onkeydown={handleKeyDown} role="application">
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
          value={`${referenceDate.getFullYear()}-${String(referenceDate.getMonth() + 1).padStart(2, "0")}-${String(referenceDate.getDate()).padStart(2, "0")}`}
          max={`${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}-${String(new Date().getDate()).padStart(2, "0")}`}
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

  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  <div class="main-content">
    <!-- Split view: list on left, detail on right -->
    <div class="split-view">
      <!-- Account list (left) -->
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
        <!-- Net Worth Summary (Always visible) -->
        <div class="net-worth-summary">
          <div class="net-worth-main">
            <div class="net-worth-left">
              <span class="net-worth-label">NET WORTH</span>
              <span class="net-worth-value" class:negative={netWorth < 0}>
                {formatCurrency(netWorth)}
              </span>
              {#if momChange}
                <span class="net-worth-change" class:positive={momChange.change >= 0} class:negative={momChange.change < 0}>
                  {momChange.change >= 0 ? "+" : ""}{formatCurrency(momChange.change)} this month
                </span>
              {/if}
            </div>
            <div class="net-worth-right">
              {#if sparklineData.length >= 2}
                <Sparkline data={sparklineData} width={80} height={24} />
              {/if}
              <button
                class="expand-toggle"
                onclick={() => (netWorthExpanded = !netWorthExpanded)}
                title={netWorthExpanded ? "Collapse chart" : "Expand chart"}
              >
                {netWorthExpanded ? "−" : "+"}
              </button>
            </div>
          </div>
          <div class="net-worth-breakdown-inline">
            <span class="breakdown-item">
              <span class="breakdown-dot asset"></span>
              Assets {formatCurrencyCompact(totalAssets)}
            </span>
            <span class="breakdown-item">
              <span class="breakdown-dot liability"></span>
              Liabilities {formatCurrencyCompact(totalLiabilities)}
            </span>
          </div>

          {#if netWorthExpanded && netWorthChartData.length >= 2}
            <div class="net-worth-chart">
              <div class="chart-header">
                <div class="time-range-selector">
                  {#each timeRangeOptions as option}
                    <button
                      class="time-range-btn"
                      class:active={chartTimeRange === option.value}
                      onclick={() => (chartTimeRange = option.value)}
                    >
                      {option.label}
                    </button>
                  {/each}
                </div>
              </div>
              <LineAreaChart
                data={netWorthChartData}
                height={100}
                showArea={true}
                showLine={true}
                showLabels={true}
                showZeroLine={true}
                formatValue={formatCurrency}
              />
              {#if periodChange}
                <div class="chart-summary" class:positive={periodChange.change >= 0} class:negative={periodChange.change < 0}>
                  {periodChange.change >= 0 ? "+" : ""}{formatCurrency(periodChange.change)}
                  ({periodChange.percent >= 0 ? "+" : ""}{periodChange.percent.toFixed(1)}%)
                  over {periodChange.days} days
                </div>
              {/if}
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
              {@const monthChange = accountMonthlyChanges.get(account.account_id)}
              <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
              <div
                class="row"
                class:cursor={cursorIndex === globalIndex}
                class:excluded={config.excludedFromNetWorth.includes(account.account_id)}
                data-index={globalIndex}
                onclick={() => handleRowClick(globalIndex)}
                ondblclick={() => handleRowDoubleClick(globalIndex)}
                onkeydown={(e) => e.key === 'Enter' && handleRowDoubleClick(globalIndex)}
                role="option"
                aria-selected={cursorIndex === globalIndex}
                tabindex={cursorIndex === globalIndex ? 0 : -1}
              >
                <div class="row-name">
                  <span class="account-name">{getDisplayName(account)}</span>
                  {#if getSubtitle(account)}
                    <span class="account-subtitle">{getSubtitle(account)}</span>
                  {/if}
                </div>
                <div class="row-balance">{account.balance !== null ? formatCurrency(getBalanceForDisplay(account)) : "—"}</div>
                {#if monthChange}
                  {@const isGoodChange = monthChange.change >= 0}
                  <div class="row-change" class:positive={isGoodChange} class:negative={!isGoodChange}>
                    <span class="change-value">{monthChange.change >= 0 ? "+" : ""}{formatCurrencyCompact(monthChange.change)}</span>
                    <span class="change-label">MoM</span>
                  </div>
                {:else}
                  <div class="row-change"></div>
                {/if}
                <RowMenu
                  items={[
                    { label: "Edit", action: () => { startEdit(account); closeAccountMenu(); } },
                    { label: "Set Balance", action: () => openSetBalanceModal(account) },
                    { label: "Import CSV", action: () => openImportModal(account) },
                    { label: "Delete", action: () => { deleteAccount(account); closeAccountMenu(); }, danger: true, disabled: account.transaction_count > 0, disabledReason: account.transaction_count > 0 ? "has transactions" : undefined },
                  ]}
                  isOpen={menuOpenForAccount === account.account_id}
                  onToggle={(e) => toggleAccountMenu(account.account_id, e)}
                  onClose={closeAccountMenu}
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
              {@const monthChange = accountMonthlyChanges.get(account.account_id)}
              <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
              <div
                class="row"
                class:cursor={cursorIndex === globalIndex}
                class:excluded={config.excludedFromNetWorth.includes(account.account_id)}
                data-index={globalIndex}
                onclick={() => handleRowClick(globalIndex)}
                ondblclick={() => handleRowDoubleClick(globalIndex)}
                onkeydown={(e) => e.key === 'Enter' && handleRowDoubleClick(globalIndex)}
                role="option"
                aria-selected={cursorIndex === globalIndex}
                tabindex={cursorIndex === globalIndex ? 0 : -1}
              >
                <div class="row-name">
                  <span class="account-name">{getDisplayName(account)}</span>
                  {#if getSubtitle(account)}
                    <span class="account-subtitle">{getSubtitle(account)}</span>
                  {/if}
                </div>
                <div class="row-balance liability">{account.balance !== null ? formatCurrency(Math.abs(getBalanceForDisplay(account))) : "—"}</div>
                {#if monthChange}
                  {@const isGoodChange = monthChange.change <= 0}
                  <div class="row-change" class:positive={isGoodChange} class:negative={!isGoodChange}>
                    <span class="change-value">{monthChange.change > 0 ? "+" : ""}{formatCurrencyCompact(monthChange.change)}</span>
                    <span class="change-label">MoM</span>
                  </div>
                {:else}
                  <div class="row-change"></div>
                {/if}
                <RowMenu
                  items={[
                    { label: "Edit", action: () => { startEdit(account); closeAccountMenu(); } },
                    { label: "Set Balance", action: () => openSetBalanceModal(account) },
                    { label: "Import CSV", action: () => openImportModal(account) },
                    { label: "Delete", action: () => { deleteAccount(account); closeAccountMenu(); }, danger: true, disabled: account.transaction_count > 0, disabledReason: account.transaction_count > 0 ? "has transactions" : undefined },
                  ]}
                  isOpen={menuOpenForAccount === account.account_id}
                  onToggle={(e) => toggleAccountMenu(account.account_id, e)}
                  onClose={closeAccountMenu}
                  title="Account actions"
                />
              </div>
            {/each}
          </div>
        {/if}
      {/if}
      </div>

      <!-- Detail Panel (Right side) -->
      {#if currentAccount && showDetailPanel && !isLoading}
        <div class="detail-panel">
          <div class="detail-header">
            <div class="detail-account-info">
              <span class="detail-account-name">{getDisplayName(currentAccount)}</span>
              {#if getSubtitle(currentAccount)}
                <span class="detail-account-subtitle">{getSubtitle(currentAccount)}</span>
              {/if}
            </div>
            <button class="detail-close" onclick={() => showDetailPanel = false} title="Close (Esc)">×</button>
          </div>

          <div class="detail-content">
            <div class="detail-balance-section">
              <div class="detail-balance-main">
                <span class="detail-balance-value" class:liability={currentAccount.classification === 'liability'}>
                  {currentAccount.balance !== null ? formatCurrency(Math.abs(getBalanceForDisplay(currentAccount))) : "—"}
                </span>
              </div>
              {#if balanceTrend.length >= 2}
                {@const current = balanceTrend[balanceTrend.length - 1]}
                {@const previous = balanceTrend[balanceTrend.length - 2]}
                {@const change = current.balance - previous.balance}
                {@const percent = previous.balance !== 0 ? (change / Math.abs(previous.balance)) * 100 : 0}
                {@const isLiability = currentAccount.classification === 'liability'}
                {@const isGoodChange = isLiability ? change <= 0 : change >= 0}
                <div class="detail-balance-change" class:positive={isGoodChange} class:negative={!isGoodChange}>
                  {change >= 0 ? "+" : ""}{formatCurrency(change)} ({percent >= 0 ? "+" : ""}{percent.toFixed(1)}%) vs last month
                </div>
              {/if}
            </div>

            {#if balanceTrendChartData.length >= 2}
              <div class="detail-chart">
                <div class="detail-chart-title">Balance History ({allBalanceSnapshots.length} snapshots)</div>
                <LineAreaChart
                  data={balanceTrendChartData}
                  height={100}
                  showArea={true}
                  showLine={true}
                  showLabels={true}
                  formatValue={formatCurrency}
                  invertTrend={currentAccount.classification === 'liability'}
                />
              </div>
            {/if}

            <div class="detail-meta">
              <div class="detail-meta-item">
                <span class="detail-meta-label">Type</span>
                <span class="detail-meta-value">{currentAccount.account_type || "—"}</span>
              </div>
              <div class="detail-meta-item">
                <span class="detail-meta-label">Classification</span>
                <span class="detail-meta-value">{currentAccount.classification}</span>
              </div>
              <div class="detail-meta-item">
                <span class="detail-meta-label">Transactions</span>
                <span class="detail-meta-value">{currentAccount.transaction_count.toLocaleString()}</span>
              </div>
              {#if currentAccount.first_transaction}
                <div class="detail-meta-item">
                  <span class="detail-meta-label">First Transaction</span>
                  <span class="detail-meta-value">{currentAccount.first_transaction}</span>
                </div>
              {/if}
              {#if currentAccount.last_transaction}
                <div class="detail-meta-item">
                  <span class="detail-meta-label">Last Transaction</span>
                  <span class="detail-meta-value">{currentAccount.last_transaction}</span>
                </div>
              {/if}
            </div>

            <div class="detail-actions">
              <button class="btn secondary" onclick={() => openSetBalanceModal(currentAccount)}>Set Balance</button>
              <button class="btn secondary" onclick={() => openImportModal(currentAccount)}>Import CSV</button>
              <button class="btn secondary" onclick={() => showPreview(currentAccount)}>View Txns</button>
              <button class="btn secondary" onclick={() => startEdit(currentAccount)}>Edit</button>
            </div>

            <div class="snapshot-section">
              <div class="snapshot-title">Balance History</div>
              {#if detailSnapshotsLoading}
                <div class="snapshot-loading">Loading...</div>
              {:else if detailSnapshots.length === 0}
                <div class="snapshot-empty">
                  <span>No balance snapshots</span>
                  <button class="btn-link" onclick={() => openSetBalanceModal(currentAccount)}>Add one</button>
                </div>
              {:else}
                <div class="snapshot-list">
                  <div class="snapshot-header-row">
                    <span class="snapshot-col-date">Date</span>
                    <span class="snapshot-col-balance">Balance</span>
                    <span class="snapshot-col-source">Source</span>
                    <span class="snapshot-col-actions"></span>
                  </div>
                  {#each detailSnapshots as snapshot}
                    <div class="snapshot-row">
                      <span class="snapshot-col-date">{snapshot.snapshot_time.split("T")[0]}</span>
                      <span class="snapshot-col-balance">{formatCurrency(snapshot.balance)}</span>
                      <span class="snapshot-col-source">{snapshot.source || "—"}</span>
                      <span class="snapshot-col-actions">
                        <button
                          class="snapshot-delete-btn"
                          onclick={() => deleteSnapshot(snapshot.snapshot_id)}
                          title="Delete snapshot"
                        >×</button>
                      </span>
                    </div>
                  {/each}
                </div>
                <div class="snapshot-footer">
                  <span class="snapshot-count">{detailSnapshots.length} snapshot{detailSnapshots.length !== 1 ? "s" : ""}</span>
                  <button class="btn-link" onclick={() => openSetBalanceModal(currentAccount)}>Add new</button>
                </div>
              {/if}
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Keyboard shortcuts footer -->
  <div class="shortcuts-footer">
    <span class="shortcut"><kbd>j</kbd><kbd>k</kbd> nav</span>
    <span class="shortcut"><kbd>Enter</kbd> view txns</span>
    <span class="shortcut"><kbd>s</kbd> set balance</span>
    <span class="shortcut"><kbd>e</kbd> edit</span>
    <span class="shortcut"><kbd>a</kbd> add</span>
    <span class="shortcut"><kbd>Tab</kbd> toggle panel</span>
  </div>

  <Modal
    open={showTransactionPreview && !!previewAccount}
    title={previewAccount?.nickname || previewAccount?.name || ""}
    onclose={closePreview}
    width="500px"
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
      {#if editingAccount?.isManual}
        <label>
          Account Name *
          <input
            type="text"
            bind:value={editForm.name}
            placeholder="e.g., Emergency Fund"
          />
        </label>
        <label>
          Institution (optional)
          <input
            type="text"
            bind:value={editForm.institution_name}
            placeholder="e.g., Vanguard, Manual"
          />
        </label>
      {:else}
        <label>
          Account Name (from source)
          <input type="text" value={editingAccount?.name ?? ""} disabled />
          <span class="form-hint">Synced from connected account - cannot be edited</span>
        </label>
      {/if}
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

  <CsvImportModal
    open={showImportModal}
    accountId={importAccountId}
    accountName={importAccountName}
    onclose={closeImportModal}
    onsuccess={handleImportSuccess}
  />

  <SetBalanceModal
    open={showSetBalanceModal}
    accountId={setBalanceAccountId}
    accountName={setBalanceAccountName}
    currentBalance={setBalanceCurrentBalance}
    currentBalanceDate={setBalanceCurrentDate}
    onclose={closeSetBalanceModal}
    onsave={handleSetBalanceSave}
  />
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
    flex-direction: column;
    overflow: hidden;
  }

  .split-view {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .list-container {
    flex: 1;
    overflow-y: auto;
    font-family: var(--font-mono);
    font-size: 13px;
    min-width: 0;
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

  /* Net Worth Summary */
  .net-worth-summary {
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-primary);
  }

  .net-worth-main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--spacing-sm);
  }

  .net-worth-left {
    display: flex;
    align-items: baseline;
    gap: var(--spacing-md);
    flex-wrap: wrap;
  }

  .net-worth-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .net-worth-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .net-worth-value.negative {
    color: var(--accent-danger, #ef4444);
  }

  .net-worth-change {
    font-size: 12px;
    font-weight: 500;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .net-worth-change.positive {
    color: var(--accent-success, #22c55e);
  }

  .net-worth-change.negative {
    color: var(--accent-danger, #ef4444);
  }

  .net-worth-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .expand-toggle {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-muted);
    font-size: 16px;
    cursor: pointer;
  }

  .expand-toggle:hover {
    color: var(--text-primary);
    background: var(--bg-primary);
  }

  .net-worth-breakdown-inline {
    display: flex;
    gap: var(--spacing-lg);
    font-size: 12px;
    color: var(--text-muted);
  }

  .breakdown-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
  }

  .breakdown-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .breakdown-dot.asset {
    background: var(--accent-success, #22c55e);
  }

  .breakdown-dot.liability {
    background: var(--accent-danger, #ef4444);
  }

  .net-worth-chart {
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--border-primary);
  }

  .chart-header {
    display: flex;
    justify-content: flex-end;
    margin-bottom: var(--spacing-sm);
  }

  .time-range-selector {
    display: flex;
    gap: 2px;
    background: var(--bg-primary);
    border-radius: 4px;
    padding: 2px;
  }

  .time-range-btn {
    padding: 4px 8px;
    font-size: 10px;
    font-weight: 500;
    color: var(--text-muted);
    background: transparent;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .time-range-btn:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }

  .time-range-btn.active {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }

  .chart-summary {
    margin-top: var(--spacing-sm);
    font-size: 11px;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .chart-summary.positive {
    color: var(--accent-success, #22c55e);
  }

  .chart-summary.negative {
    color: var(--accent-danger, #ef4444);
  }

  /* Sections */
  .section {
    margin-bottom: var(--spacing-xs);
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

  /* Account Rows */
  .row {
    display: flex;
    align-items: center;
    padding: 10px var(--spacing-lg);
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
    font-weight: 500;
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

  .row-change {
    width: 80px;
    text-align: right;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 1px;
  }

  .row-change .change-value {
    font-family: var(--font-mono);
  }

  .row-change .change-label {
    font-size: 9px;
    color: var(--text-muted);
    opacity: 0.7;
  }

  .row-change.positive .change-value {
    color: var(--accent-success, #22c55e);
  }

  .row-change.negative .change-value {
    color: var(--accent-danger, #ef4444);
  }

  /* Detail Panel (Right side split view) */
  .detail-panel {
    width: 320px;
    flex-shrink: 0;
    border-left: 1px solid var(--border-primary);
    background: var(--bg-secondary);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
    background: var(--bg-tertiary);
    flex-shrink: 0;
  }

  .detail-account-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .detail-account-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .detail-account-subtitle {
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .detail-close {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 18px;
    cursor: pointer;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .detail-close:hover {
    background: var(--bg-primary);
    color: var(--text-primary);
  }

  .detail-content {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-md);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .detail-balance-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    text-align: center;
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
  }

  .detail-balance-main {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: var(--spacing-md);
  }

  .detail-balance-value {
    font-size: 24px;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--text-primary);
  }

  .detail-balance-value.liability {
    color: var(--accent-danger, #ef4444);
  }

  .detail-balance-change {
    font-size: 12px;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .detail-balance-change.positive {
    color: var(--accent-success, #22c55e);
  }

  .detail-balance-change.negative {
    color: var(--accent-danger, #ef4444);
  }

  .detail-chart {
    flex-shrink: 0;
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
  }

  .detail-chart-title {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--spacing-sm);
  }

  .detail-meta {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    font-size: 12px;
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
  }

  .detail-meta-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .detail-meta-label {
    color: var(--text-muted);
  }

  .detail-meta-value {
    font-family: var(--font-mono);
    color: var(--text-primary);
  }

  .detail-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-xs);
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
  }

  .detail-actions .btn {
    font-size: 11px;
    padding: 6px 8px;
  }

  /* Snapshot Section */
  .snapshot-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .snapshot-title {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--spacing-sm);
    flex-shrink: 0;
  }

  .snapshot-loading,
  .snapshot-empty {
    font-size: 12px;
    color: var(--text-muted);
    padding: var(--spacing-sm) 0;
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .snapshot-list {
    font-size: 11px;
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .snapshot-header-row {
    display: grid;
    grid-template-columns: 80px 1fr 50px 24px;
    gap: var(--spacing-xs);
    padding: var(--spacing-xs) 0;
    color: var(--text-muted);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border-primary);
    position: sticky;
    top: 0;
    background: var(--bg-secondary);
  }

  .snapshot-row {
    display: grid;
    grid-template-columns: 80px 1fr 50px 24px;
    gap: var(--spacing-xs);
    padding: var(--spacing-xs) 0;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-primary);
  }

  .snapshot-row:last-child {
    border-bottom: none;
  }

  .snapshot-col-date {
    font-family: var(--font-mono);
  }

  .snapshot-col-balance {
    font-family: var(--font-mono);
    font-weight: 500;
  }

  .snapshot-col-source {
    color: var(--text-muted);
    font-size: 10px;
  }

  .snapshot-col-actions {
    text-align: right;
  }

  .snapshot-delete-btn {
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 14px;
    cursor: pointer;
    border-radius: 3px;
    opacity: 0.5;
    transition: opacity 0.15s, color 0.15s, background-color 0.15s;
  }

  .snapshot-delete-btn:hover {
    opacity: 1;
    color: var(--accent-danger);
    background: rgba(239, 68, 68, 0.1);
  }

  .snapshot-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: var(--spacing-sm);
    margin-top: var(--spacing-sm);
    border-top: 1px solid var(--border-primary);
    font-size: 11px;
    color: var(--text-muted);
  }

  .snapshot-count {
    font-family: var(--font-mono);
  }

  .btn-link {
    background: none;
    border: none;
    color: var(--accent-primary);
    font-size: 11px;
    cursor: pointer;
    padding: 0;
  }

  .btn-link:hover {
    text-decoration: underline;
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

  /* Utility classes */
  .positive {
    color: var(--accent-success, #22c55e) !important;
  }

  .negative {
    color: var(--accent-danger, #ef4444) !important;
  }

  /* Button styles */
  .btn {
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }

  .btn.primary {
    background: var(--accent-primary);
    border: none;
    color: white;
  }

  .btn.primary:hover {
    opacity: 0.9;
  }

  .btn.secondary {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    color: var(--text-primary);
  }

  .btn.secondary:hover {
    background: var(--bg-primary);
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
    color: var(--accent-danger, #ef4444);
  }

  .modal-footer {
    padding: var(--spacing-sm) var(--spacing-lg);
    font-size: 11px;
    color: var(--text-muted);
    background: var(--bg-tertiary);
  }
</style>
