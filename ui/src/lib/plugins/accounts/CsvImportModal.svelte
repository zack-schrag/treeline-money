<script lang="ts">
  /**
   * CsvImportModal - Modal for importing transactions from CSV files
   * After import, shows unified flow for setting balance and backfilling history
   */
  import { Modal, Icon } from "../../shared";
  import {
    pickCsvFile,
    getCsvHeaders,
    importCsvPreview,
    importCsvExecute,
    executeQuery,
    getDemoMode,
    runBackfill,
    type ImportColumnMapping,
    type ImportPreviewResult,
    type ImportExecuteResult,
  } from "../../sdk";

  interface Props {
    open: boolean;
    accountId: string;
    accountName: string;
    onclose: () => void;
    onsuccess: () => void;
  }

  let { open, accountId, accountName, onclose, onsuccess }: Props = $props();

  // Balance state for post-import flow
  let existingBalance = $state<number | null>(null);
  let existingBalanceDate = $state<string | null>(null);
  let balanceInput = $state("");
  let balanceDateInput = $state("");
  let runBackfillChecked = $state(false);
  let isSavingBalance = $state(false);
  let balanceError = $state<string | null>(null);

  // Import state
  let filePath = $state("");
  let fileName = $state("");
  let headers = $state<string[]>([]);
  let columnMapping = $state<ImportColumnMapping>({});
  let flipSigns = $state(false);
  let debitNegative = $state(false);
  let preview = $state<ImportPreviewResult | null>(null);
  let result = $state<ImportExecuteResult | null>(null);
  let error = $state<string | null>(null);
  let isImporting = $state(false);
  let isLoadingPreview = $state(false);
  let previewDebounceTimer: ReturnType<typeof setTimeout> | null = null;
  let demoModeWarning = $state(false);

  // Reset state when modal opens
  $effect(() => {
    if (open) {
      filePath = "";
      fileName = "";
      headers = [];
      columnMapping = {};
      flipSigns = false;
      debitNegative = false;
      preview = null;
      result = null;
      error = null;
      isImporting = false;
      isLoadingPreview = false;
      // Reset balance state
      existingBalance = null;
      existingBalanceDate = null;
      balanceInput = "";
      balanceDateInput = new Date().toISOString().split("T")[0];
      runBackfillChecked = false;
      isSavingBalance = false;
      balanceError = null;
      checkDemoMode();
    }
  });

  async function checkDemoMode() {
    demoModeWarning = await getDemoMode();
  }

  // Load existing balance for the account
  async function loadExistingBalance() {
    try {
      const res = await executeQuery(`
        SELECT balance, snapshot_time
        FROM sys_balance_snapshots
        WHERE account_id = '${accountId}'
        ORDER BY snapshot_time DESC
        LIMIT 1
      `);
      if (res.rows.length > 0) {
        existingBalance = res.rows[0][0] as number;
        const snapshotTime = res.rows[0][1] as string;
        existingBalanceDate = snapshotTime.split("T")[0];
        // Pre-fill the balance input
        balanceInput = Math.abs(existingBalance).toFixed(2);
      }
    } catch (e) {
      console.error("Failed to load existing balance", e);
    }
  }

  // Save balance snapshot
  async function saveBalance() {
    const balance = parseFloat(balanceInput);
    if (isNaN(balance)) {
      balanceError = "Please enter a valid balance";
      return;
    }

    isSavingBalance = true;
    balanceError = null;

    try {
      const snapshotId = crypto.randomUUID();
      const snapshotTime = `${balanceDateInput}T23:59:59`;
      const now = new Date().toISOString();

      await executeQuery(
        `INSERT INTO sys_balance_snapshots (snapshot_id, account_id, balance, snapshot_time, created_at, updated_at, source)
         VALUES ('${snapshotId}', '${accountId}', ${balance}, '${snapshotTime}', '${now}', '${now}', 'manual')`,
        { readonly: false }
      );

      // Update existing balance state
      existingBalance = balance;
      existingBalanceDate = balanceDateInput;

      // Run backfill if checkbox is checked
      if (runBackfillChecked) {
        try {
          await runBackfill(accountId);
        } catch (backfillError) {
          console.error("Backfill failed:", backfillError);
          // Don't fail the whole save, just log the error
          // The balance was saved successfully
        }
      }
    } catch (e) {
      balanceError = e instanceof Error ? e.message : "Failed to save balance";
    } finally {
      isSavingBalance = false;
    }
  }

  // Derived: can run backfill (need a balance)
  let canBackfill = $derived(existingBalance !== null || balanceInput.trim() !== "");

  // Derived: is balance form valid
  let isBalanceValid = $derived(() => {
    const balance = parseFloat(balanceInput);
    return !isNaN(balance) && balanceDateInput.length === 10;
  });

  // Auto-update preview when mapping or options change
  $effect(() => {
    if (filePath && accountId && open) {
      // Trigger on any of these changing
      const _ = [columnMapping, flipSigns, debitNegative];
      debouncedPreview();
    }
  });

  function debouncedPreview() {
    if (previewDebounceTimer) {
      clearTimeout(previewDebounceTimer);
    }
    previewDebounceTimer = setTimeout(() => {
      loadPreview();
    }, 300);
  }

  async function loadPreview() {
    if (!filePath || !accountId) return;

    isLoadingPreview = true;
    try {
      preview = await importCsvPreview(
        filePath,
        accountId,
        columnMapping,
        flipSigns,
        debitNegative
      );
      error = null;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to preview CSV";
    } finally {
      isLoadingPreview = false;
    }
  }

  async function handleFileSelect() {
    const path = await pickCsvFile();
    if (!path) return;

    filePath = path;
    fileName = path.split("/").pop() || path;

    try {
      headers = await getCsvHeaders(path);
      // Auto-detect columns
      columnMapping = autoDetectColumns(headers);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to read CSV headers";
    }
  }

  function autoDetectColumns(headers: string[]): ImportColumnMapping {
    const mapping: ImportColumnMapping = {};
    const lowerHeaders = headers.map((h) => h.toLowerCase());

    // Date detection
    const datePatterns = ["date", "transaction date", "posted", "trans date"];
    for (const pattern of datePatterns) {
      const idx = lowerHeaders.findIndex((h) => h.includes(pattern));
      if (idx >= 0) {
        mapping.dateColumn = headers[idx];
        break;
      }
    }

    // Description detection
    const descPatterns = ["description", "desc", "memo", "narrative", "details"];
    for (const pattern of descPatterns) {
      const idx = lowerHeaders.findIndex((h) => h.includes(pattern));
      if (idx >= 0) {
        mapping.descriptionColumn = headers[idx];
        break;
      }
    }

    // Amount detection
    const amountPatterns = ["amount", "total"];
    for (const pattern of amountPatterns) {
      const idx = lowerHeaders.findIndex(
        (h) => h.includes(pattern) && !h.includes("debit") && !h.includes("credit")
      );
      if (idx >= 0) {
        mapping.amountColumn = headers[idx];
        break;
      }
    }

    // Debit/Credit detection (if no single amount column found)
    if (!mapping.amountColumn) {
      const debitIdx = lowerHeaders.findIndex((h) => h.includes("debit"));
      const creditIdx = lowerHeaders.findIndex((h) => h.includes("credit"));
      if (debitIdx >= 0) {
        mapping.debitColumn = headers[debitIdx];
      }
      if (creditIdx >= 0) {
        mapping.creditColumn = headers[creditIdx];
      }
    }

    return mapping;
  }

  async function handleImportExecute() {
    if (!filePath || !accountId) return;

    isImporting = true;
    error = null;

    try {
      result = await importCsvExecute(
        filePath,
        accountId,
        columnMapping,
        flipSigns,
        debitNegative
      );
      // After successful import, load existing balance for post-import flow
      await loadExistingBalance();
    } catch (e) {
      error = e instanceof Error ? e.message : "Import failed";
    } finally {
      isImporting = false;
    }
  }

  function handleClose() {
    if (result) {
      onsuccess();
    }
    onclose();
  }

  function handleChangeFile() {
    filePath = "";
    headers = [];
    columnMapping = {};
    preview = null;
  }
</script>

<Modal
  open={open}
  title="Import CSV to {accountName}"
  onclose={handleClose}
  width="550px"
>
  <div class="import-body">
    {#if demoModeWarning}
      <div class="import-demo-warning">
        <span class="warning-icon"><Icon name="beaker" size={16} /></span>
        <div class="warning-content">
          <strong>Demo Mode Active</strong>
          <p>This data will be imported to the demo database, not your real data.</p>
        </div>
      </div>
    {/if}

    {#if error}
      <div class="import-error">{error}</div>
    {/if}

    {#if result}
      <!-- Import complete - unified post-import flow -->
      <div class="import-done">
        <div class="done-header">
          <div class="done-icon">✓</div>
          <div class="done-text">
            <p class="done-message">Import Complete</p>
            <p class="done-stats">{result.imported} imported, {result.skipped} skipped</p>
          </div>
        </div>

        <div class="balance-section">
          <div class="balance-header">
            <span class="balance-title">Account Balance</span>
          </div>

          {#if existingBalance !== null}
            <div class="balance-current">
              <span class="balance-amount">${Math.abs(existingBalance).toFixed(2)}</span>
              <span class="balance-date">as of {existingBalanceDate}</span>
              <button class="btn-link" onclick={() => { existingBalance = null; }}>Update</button>
            </div>
          {:else}
            <div class="balance-form">
              {#if balanceError}
                <div class="balance-error">{balanceError}</div>
              {/if}
              <p class="balance-hint">
                To track this account's balance, enter the current balance from your bank.
              </p>
              <div class="balance-inputs">
                <div class="input-group">
                  <label for="balance-amount">Balance</label>
                  <div class="input-with-prefix">
                    <span class="input-prefix">$</span>
                    <input
                      id="balance-amount"
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      bind:value={balanceInput}
                    />
                  </div>
                </div>
                <div class="input-group">
                  <label for="balance-date">As of</label>
                  <input
                    id="balance-date"
                    type="date"
                    bind:value={balanceDateInput}
                  />
                </div>
              </div>
            </div>
          {/if}

          <div class="backfill-section">
            <label class="checkbox-label" class:disabled={!canBackfill}>
              <input type="checkbox" bind:checked={runBackfillChecked} disabled={!canBackfill} />
              <span class="checkbox-content">
                <span class="checkbox-title">Calculate historical balances</span>
                <span class="checkbox-desc">
                  {#if canBackfill}
                    Estimate past balances from your transaction history
                  {:else}
                    Set a balance first to enable this option
                  {/if}
                </span>
              </span>
            </label>
          </div>
        </div>
      </div>
    {:else if !filePath}
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
          <span class="file-name">{fileName}</span>
          <button class="btn-link" onclick={handleChangeFile}>Change</button>
        </div>

        <div class="column-mapping">
          <div class="mapping-title">Column Mapping</div>
          <div class="mapping-hint">Auto-detected. Adjust if needed.</div>

          <div class="mapping-row">
            <label for="date-column-select">Date Column</label>
            <select id="date-column-select" bind:value={columnMapping.dateColumn}>
              <option value="">-- Select --</option>
              {#each headers as header}
                <option value={header}>{header}</option>
              {/each}
            </select>
          </div>

          <div class="mapping-row">
            <label for="description-column-select">Description Column</label>
            <select id="description-column-select" bind:value={columnMapping.descriptionColumn}>
              <option value="">-- Select --</option>
              {#each headers as header}
                <option value={header}>{header}</option>
              {/each}
            </select>
          </div>

          <!-- Amount options: Single column OR Debit/Credit -->
          <div class="amount-options">
            <div class="amount-option" class:active={!!columnMapping.amountColumn}>
              <div class="option-header">
                <span class="option-label">Option 1</span>
                <span class="option-desc">Single amount column</span>
              </div>
              <select
                bind:value={columnMapping.amountColumn}
                onchange={() => { if (columnMapping.amountColumn) { columnMapping.debitColumn = ''; columnMapping.creditColumn = ''; }}}
              >
                <option value="">-- Select --</option>
                {#each headers as header}
                  <option value={header}>{header}</option>
                {/each}
              </select>
            </div>

            <div class="option-divider">
              <span class="divider-text">OR</span>
            </div>

            <div class="amount-option" class:active={!!columnMapping.debitColumn || !!columnMapping.creditColumn}>
              <div class="option-header">
                <span class="option-label">Option 2</span>
                <span class="option-desc">Separate debit/credit columns</span>
              </div>
              <div class="dual-select">
                <select
                  bind:value={columnMapping.debitColumn}
                  onchange={() => { if (columnMapping.debitColumn) columnMapping.amountColumn = ''; }}
                >
                  <option value="">Debit...</option>
                  {#each headers as header}
                    <option value={header}>{header}</option>
                  {/each}
                </select>
                <select
                  bind:value={columnMapping.creditColumn}
                  onchange={() => { if (columnMapping.creditColumn) columnMapping.amountColumn = ''; }}
                >
                  <option value="">Credit...</option>
                  {#each headers as header}
                    <option value={header}>{header}</option>
                  {/each}
                </select>
              </div>
            </div>
          </div>
        </div>

        <div class="import-options">
          <label class="checkbox-label">
            <input type="checkbox" bind:checked={flipSigns} />
            Flip signs (for credit cards where charges are positive)
          </label>
          <label class="checkbox-label">
            <input type="checkbox" bind:checked={debitNegative} />
            Negate debits (if debits show as positive numbers)
          </label>
        </div>

        <!-- Live Preview -->
        {#if columnMapping.dateColumn && (columnMapping.amountColumn || columnMapping.debitColumn || columnMapping.creditColumn)}
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

            {#if preview && preview.preview.length > 0}
              <div class="preview-table">
                <div class="preview-row header">
                  <span class="preview-date">Date</span>
                  <span class="preview-desc">Description</span>
                  <span class="preview-amount">Amount</span>
                </div>
                {#each preview.preview.slice(0, 5) as txn}
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
    {#if result}
      {#if existingBalance === null && balanceInput.trim()}
        <button class="btn secondary" onclick={handleClose}>Skip</button>
        <button class="btn primary" onclick={saveBalance} disabled={!isBalanceValid() || isSavingBalance}>
          {isSavingBalance ? "Saving..." : "Save & Done"}
        </button>
      {:else}
        <button class="btn primary" onclick={handleClose}>Done</button>
      {/if}
    {:else if isImporting}
      <button class="btn secondary" disabled>Importing...</button>
    {:else}
      <button class="btn secondary" onclick={handleClose}>Cancel</button>
      {#if filePath && preview && preview.preview.length > 0}
        <button class="btn primary" onclick={handleImportExecute}>Import</button>
      {/if}
    {/if}
  {/snippet}
</Modal>

<style>
  .import-body {
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .import-demo-warning {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    background: rgba(251, 191, 36, 0.15);
    border: 1px solid rgba(251, 191, 36, 0.4);
    border-radius: 6px;
    color: var(--text-primary);
  }

  .warning-icon {
    color: rgb(251, 191, 36);
    flex-shrink: 0;
    margin-top: 2px;
  }

  .warning-content strong {
    display: block;
    font-size: 13px;
    margin-bottom: 4px;
  }

  .warning-content p {
    margin: 0;
    font-size: 12px;
    color: var(--text-muted);
  }

  .import-error {
    padding: var(--spacing-md);
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 6px;
    color: var(--accent-danger, #ef4444);
    font-size: 13px;
  }

  .import-done {
    padding: var(--spacing-md);
  }

  .done-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
  }

  .done-icon {
    width: 36px;
    height: 36px;
    background: var(--accent-success, #22c55e);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
  }

  .done-text {
    flex: 1;
  }

  .done-message {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .done-stats {
    font-size: 13px;
    color: var(--text-muted);
    margin: 2px 0 0 0;
  }

  .balance-section {
    background: var(--bg-tertiary);
    border-radius: 8px;
    padding: var(--spacing-md);
  }

  .balance-header {
    margin-bottom: var(--spacing-sm);
  }

  .balance-title {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .balance-current {
    display: flex;
    align-items: baseline;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) 0;
  }

  .balance-amount {
    font-size: 20px;
    font-weight: 600;
    font-family: var(--font-mono);
    color: var(--text-primary);
  }

  .balance-date {
    font-size: 13px;
    color: var(--text-muted);
  }

  .balance-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .balance-error {
    padding: var(--spacing-sm);
    background: rgba(239, 68, 68, 0.15);
    border-radius: 4px;
    color: var(--accent-danger, #ef4444);
    font-size: 12px;
  }

  .balance-hint {
    margin: 0;
    font-size: 13px;
    color: var(--text-muted);
  }

  .balance-inputs {
    display: flex;
    gap: var(--spacing-md);
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
  }

  .input-group label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
  }

  .input-with-prefix {
    display: flex;
    align-items: center;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    overflow: hidden;
  }

  .input-with-prefix:focus-within {
    border-color: var(--accent-primary);
  }

  .input-prefix {
    padding: 6px 10px;
    background: var(--bg-secondary);
    color: var(--text-muted);
    font-size: 13px;
    border-right: 1px solid var(--border-primary);
  }

  .input-with-prefix input {
    flex: 1;
    padding: 6px 10px;
    border: none;
    background: transparent;
    color: var(--text-primary);
    font-size: 13px;
    font-family: var(--font-mono);
    min-width: 0;
  }

  .input-with-prefix input:focus {
    outline: none;
  }

  .input-group input[type="date"] {
    padding: 6px 10px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
  }

  .input-group input[type="date"]:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .backfill-section {
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--border-primary);
  }

  .backfill-section .checkbox-label {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    cursor: pointer;
  }

  .backfill-section .checkbox-label.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .backfill-section .checkbox-label input {
    margin-top: 2px;
  }

  .checkbox-content {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .checkbox-title {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .checkbox-desc {
    font-size: 11px;
    color: var(--text-muted);
  }

  .import-step {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .import-intro {
    margin: 0;
    color: var(--text-muted);
    font-size: 14px;
  }

  .file-select-btn {
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--bg-tertiary);
    border: 2px dashed var(--border-primary);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 14px;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
  }

  .file-select-btn:hover {
    border-color: var(--accent-primary);
    background: rgba(var(--accent-primary-rgb, 99, 102, 241), 0.1);
  }

  .import-file-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: 4px;
  }

  .file-label {
    font-size: 12px;
    color: var(--text-muted);
  }

  .file-name {
    flex: 1;
    font-size: 13px;
    color: var(--text-primary);
    font-family: var(--font-mono);
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
  }

  .btn-link:hover {
    text-decoration: underline;
  }

  .column-mapping {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .mapping-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .mapping-hint {
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: var(--spacing-xs);
  }

  .mapping-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .mapping-row label {
    width: 130px;
    font-size: 12px;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .mapping-row select {
    flex: 1;
    padding: 8px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 13px;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
    padding-right: 32px;
    cursor: pointer;
  }

  .mapping-row select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .mapping-row select option {
    background: var(--bg-secondary);
    color: var(--text-primary);
    padding: 8px;
  }

  /* Amount options - two mutually exclusive choices */
  .amount-options {
    display: flex;
    gap: var(--spacing-sm);
    align-items: stretch;
    margin-top: var(--spacing-sm);
  }

  .amount-option {
    flex: 1;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    transition: border-color 0.15s, background 0.15s;
  }

  .amount-option.active {
    border-color: var(--accent-primary);
    background: rgba(99, 102, 241, 0.05);
  }

  .option-header {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-bottom: var(--spacing-sm);
  }

  .option-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .option-desc {
    font-size: 11px;
    color: var(--text-secondary);
  }

  .amount-option select {
    width: 100%;
    padding: 6px 10px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 12px;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 28px;
    cursor: pointer;
  }

  .dual-select {
    display: flex;
    gap: var(--spacing-xs);
  }

  .dual-select select {
    flex: 1;
  }

  .option-divider {
    display: flex;
    align-items: center;
    padding: 0 var(--spacing-xs);
  }

  .divider-text {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-muted);
    background: var(--bg-secondary);
    padding: 4px 8px;
    border-radius: 4px;
  }

  .import-options {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 12px;
    color: var(--text-primary);
    cursor: pointer;
  }

  .checkbox-label input {
    margin: 0;
  }

  .live-preview-section {
    margin-top: var(--spacing-sm);
    padding-top: var(--spacing-md);
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
    color: var(--accent-primary);
    font-style: italic;
  }

  .preview-hint {
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: var(--spacing-sm);
    line-height: 1.5;
  }

  .preview-hint .negative {
    color: var(--accent-danger, #ef4444);
  }

  .preview-hint .positive {
    color: var(--accent-success, #22c55e);
  }

  .preview-table {
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    overflow: hidden;
  }

  .preview-row {
    display: flex;
    padding: 6px 10px;
    gap: var(--spacing-md);
    font-size: 12px;
  }

  .preview-row.header {
    background: var(--bg-tertiary);
    font-weight: 600;
    color: var(--text-muted);
  }

  .preview-row:not(.header) {
    border-top: 1px solid var(--border-primary);
  }

  .preview-date {
    width: 80px;
    flex-shrink: 0;
    color: var(--text-muted);
  }

  .preview-desc {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-primary);
  }

  .preview-amount {
    width: 70px;
    text-align: right;
    flex-shrink: 0;
    font-family: var(--font-mono);
    color: var(--accent-success, #22c55e);
  }

  .preview-amount.negative {
    color: var(--accent-danger, #ef4444);
  }

  .preview-empty {
    padding: var(--spacing-md);
    text-align: center;
    color: var(--text-muted);
    font-size: 12px;
    font-style: italic;
  }
</style>
