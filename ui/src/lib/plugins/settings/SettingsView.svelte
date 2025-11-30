<script lang="ts">
  import { onMount } from "svelte";
  import { openUrl } from "@tauri-apps/plugin-opener";
  import {
    getSettings,
    setAppSetting,
    runSync,
    executeQuery,
    setupSimplefin,
    getIntegrationSettings,
    updateIntegrationAccountSetting,
    toast,
    themeManager,
    type Settings,
    type AppSettings,
  } from "../../sdk";

  // State
  let settings = $state<Settings | null>(null);
  let isLoading = $state(true);
  let isSyncing = $state(false);

  // Integration state
  interface Integration {
    integration_name: string;
    created_at: string;
    updated_at: string;
  }
  let integrations = $state<Integration[]>([]);
  let isLoadingIntegrations = $state(false);

  // SimpleFIN accounts and status
  interface SimplefinAccount {
    account_id: string;
    simplefin_id: string;  // The provider's account ID (from external_ids)
    name: string;
    institution_name: string;
    account_type: string | null;
    balances_only: boolean;
  }
  let simplefinAccounts = $state<SimplefinAccount[]>([]);
  let connectionWarnings = $state<string[]>([]);
  let isCheckingConnection = $state(false);
  let lastConnectionCheck = $state<Date | null>(null);
  let connectionCheckSuccess = $state<boolean | null>(null); // null = not checked, true = all good, false = has warnings
  let simplefinSettings = $state<Record<string, unknown>>({});

  // SimpleFIN setup modal
  let showSetupModal = $state(false);
  let setupToken = $state("");
  let isSettingUp = $state(false);
  let setupError = $state<string | null>(null);
  let setupSuccess = $state(false);

  // Disconnect confirmation
  let showDisconnectConfirm = $state(false);
  let disconnectingIntegration = $state<string | null>(null);

  // Active section
  type Section = "appearance" | "data" | "integrations" | "about";
  let activeSection = $state<Section>("data");

  // Sections config
  const sections: { id: Section; label: string; icon: string }[] = [
    { id: "data", label: "Data", icon: "📊" },
    { id: "integrations", label: "Integrations", icon: "🔗" },
    { id: "appearance", label: "Appearance", icon: "🎨" },
    { id: "about", label: "About", icon: "ℹ️" },
  ];

  async function loadSettings() {
    isLoading = true;
    try {
      settings = await getSettings();
    } catch (e) {
      console.error("Failed to load settings:", e);
    } finally {
      isLoading = false;
    }
  }

  async function loadIntegrations() {
    isLoadingIntegrations = true;
    try {
      const result = await executeQuery(
        "SELECT integration_name, created_at, updated_at FROM sys_integrations"
      );
      // Map array rows to objects using column names
      integrations = result.rows.map((row) => ({
        integration_name: row[0] as string,
        created_at: row[1] as string,
        updated_at: row[2] as string,
      }));
    } catch (e) {
      console.error("Failed to load integrations:", e);
      integrations = [];
    } finally {
      isLoadingIntegrations = false;
    }
  }

  // Check if SimpleFIN is connected
  let isSimplefinConnected = $derived(
    integrations.some((i) => i.integration_name === "simplefin")
  );

  // Get SimpleFIN integration details
  let simplefinIntegration = $derived(
    integrations.find((i) => i.integration_name === "simplefin")
  );

  // Group SimpleFIN accounts by institution
  let accountsByInstitution = $derived.by(() => {
    const groups = new Map<string, SimplefinAccount[]>();
    for (const account of simplefinAccounts) {
      const inst = account.institution_name || "Unknown";
      if (!groups.has(inst)) {
        groups.set(inst, []);
      }
      groups.get(inst)!.push(account);
    }
    return groups;
  });

  async function loadSimplefinAccounts() {
    try {
      // Load integration settings to get balancesOnly flags
      simplefinSettings = await getIntegrationSettings("simplefin");
      const accountSettings = (simplefinSettings.accountSettings || {}) as Record<string, { balancesOnly?: boolean }>;

      const result = await executeQuery(
        `SELECT account_id, name, institution_name, account_type, json_extract_string(external_ids, '$.simplefin') as simplefin_id
         FROM sys_accounts
         WHERE json_extract_string(external_ids, '$.simplefin') IS NOT NULL
         ORDER BY institution_name, name`
      );
      simplefinAccounts = result.rows.map((row) => {
        const simplefinId = row[4] as string;
        return {
          account_id: row[0] as string,
          simplefin_id: simplefinId,
          name: row[1] as string,
          institution_name: row[2] as string,
          account_type: row[3] as string | null,
          balances_only: accountSettings[simplefinId]?.balancesOnly || false,
        };
      });
    } catch (e) {
      console.error("Failed to load SimpleFIN accounts:", e);
      simplefinAccounts = [];
    }
  }

  async function toggleBalancesOnly(account: SimplefinAccount) {
    const newValue = !account.balances_only;
    try {
      await updateIntegrationAccountSetting("simplefin", account.simplefin_id, newValue);
      // Update local state
      account.balances_only = newValue;
      // Force reactivity by reassigning the array
      simplefinAccounts = [...simplefinAccounts];
      toast.success(
        newValue ? "Balances only enabled" : "Full sync enabled",
        `${account.name} will ${newValue ? "only sync balances" : "sync transactions and balances"}`
      );
    } catch (e) {
      console.error("Failed to update balances only setting:", e);
      toast.error("Failed to update setting", e instanceof Error ? e.message : String(e));
    }
  }

  async function checkConnection() {
    isCheckingConnection = true;
    connectionWarnings = [];
    connectionCheckSuccess = null;
    try {
      const result = await runSync({ dryRun: true });
      const simplefinResult = result.results.find((r) => r.integration === "simplefin");
      if (simplefinResult?.provider_warnings) {
        connectionWarnings = simplefinResult.provider_warnings;
      }
      if (simplefinResult?.error) {
        connectionWarnings = [simplefinResult.error];
      }
      lastConnectionCheck = new Date();
      connectionCheckSuccess = connectionWarnings.length === 0;
    } catch (e) {
      connectionWarnings = [e instanceof Error ? e.message : String(e)];
      connectionCheckSuccess = false;
    } finally {
      isCheckingConnection = false;
    }
  }

  async function openExternalUrl(url: string) {
    try {
      await openUrl(url);
    } catch (e) {
      console.error("Failed to open URL:", e);
      toast.error("Failed to open link", "Could not open external browser");
    }
  }

  function openSetupModal() {
    setupToken = "";
    setupError = null;
    setupSuccess = false;
    showSetupModal = true;
  }

  function closeSetupModal() {
    showSetupModal = false;
    setupToken = "";
    setupError = null;
    setupSuccess = false;
  }

  async function handleSetupSimplefin() {
    if (!setupToken.trim()) {
      setupError = "Please enter a setup token";
      return;
    }

    isSettingUp = true;
    setupError = null;

    try {
      await setupSimplefin(setupToken.trim());
      setupSuccess = true;
      await loadIntegrations();
    } catch (e) {
      setupError = e instanceof Error ? e.message : String(e);
    } finally {
      isSettingUp = false;
    }
  }

  async function handleSyncAfterSetup() {
    closeSetupModal();
    await handleSync();
  }

  function openDisconnectConfirm(integrationName: string) {
    disconnectingIntegration = integrationName;
    showDisconnectConfirm = true;
  }

  function closeDisconnectConfirm() {
    showDisconnectConfirm = false;
    disconnectingIntegration = null;
  }

  async function handleDisconnect() {
    if (!disconnectingIntegration) return;

    try {
      await executeQuery(
        `DELETE FROM sys_integrations WHERE integration_name = '${disconnectingIntegration}'`,
        { readonly: false }
      );
      toast.success("Disconnected", `${disconnectingIntegration} integration removed`);
      await loadIntegrations();
    } catch (e) {
      toast.error("Failed to disconnect", e instanceof Error ? e.message : String(e));
    } finally {
      closeDisconnectConfirm();
    }
  }

  async function handleThemeChange(theme: AppSettings["theme"]) {
    if (!settings) return;
    await setAppSetting("theme", theme);
    settings.app.theme = theme;
    themeManager.setTheme(theme === "system" ? "dark" : theme); // TODO: detect system theme
  }

  async function handleAutoSyncChange(enabled: boolean) {
    if (!settings) return;
    await setAppSetting("autoSyncOnStartup", enabled);
    settings.app.autoSyncOnStartup = enabled;
  }

  async function handleSync() {
    isSyncing = true;
    try {
      const result = await runSync();
      const totalAccounts = result.results.reduce(
        (sum, r) => sum + (r.accounts_synced || 0),
        0
      );
      const totalTransactions = result.results.reduce(
        (sum, r) => sum + (r.transaction_stats?.new || r.transactions_synced || 0),
        0
      );

      const errors = result.results.filter((r) => r.error);
      if (errors.length > 0) {
        toast.warning(
          "Sync completed with warnings",
          errors.map((e) => e.error).join(", ")
        );
      } else {
        toast.success(
          "Sync complete",
          `${totalAccounts} accounts, ${totalTransactions} new transactions`
        );
      }

      // Reload settings to get updated lastSyncDate
      await loadSettings();
    } catch (e) {
      toast.error("Sync failed", e instanceof Error ? e.message : String(e));
    } finally {
      isSyncing = false;
    }
  }

  function formatLastSync(dateStr: string | null): string {
    if (!dateStr) return "Never";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  onMount(async () => {
    loadSettings();
    await loadIntegrations();
    // If SimpleFIN is connected, load accounts
    if (integrations.some((i) => i.integration_name === "simplefin")) {
      loadSimplefinAccounts();
    }
  });
</script>

<div class="settings-view">
  <!-- Header -->
  <div class="header">
    <h1 class="title">Settings</h1>
  </div>

  <div class="settings-content">
    <!-- Sidebar navigation -->
    <nav class="settings-nav">
      <div class="nav-section">
        <div class="nav-section-title">GENERAL</div>
        {#each sections as section}
          <button
            class="nav-item"
            class:active={activeSection === section.id}
            onclick={() => (activeSection = section.id)}
          >
            <span class="nav-icon">{section.icon}</span>
            <span class="nav-label">{section.label}</span>
          </button>
        {/each}
      </div>
    </nav>

    <!-- Main content area -->
    <main class="settings-main">
      {#if isLoading}
        <div class="loading">Loading settings...</div>
      {:else if settings}
        {#if activeSection === "data"}
          <section class="section">
            <h2 class="section-title">Data</h2>

            <!-- Sync -->
            <div class="setting-group">
              <h3 class="group-title">Sync</h3>

              <label class="checkbox-setting">
                <input
                  type="checkbox"
                  checked={settings.app.autoSyncOnStartup}
                  onchange={(e) => handleAutoSyncChange(e.currentTarget.checked)}
                />
                <span>Auto-sync on startup (once per day)</span>
              </label>

              <div class="setting-row">
                <span class="setting-label">Last synced:</span>
                <span class="setting-value">{formatLastSync(settings.app.lastSyncDate)}</span>
              </div>

              <button
                class="btn primary"
                onclick={handleSync}
                disabled={isSyncing}
              >
                {#if isSyncing}
                  Syncing...
                {:else}
                  Sync Now
                {/if}
              </button>
            </div>
          </section>
        {:else if activeSection === "integrations"}
          <section class="section">
            <h2 class="section-title">Integrations</h2>

            <!-- SimpleFIN Card -->
            <div class="integration-card">
              <div class="integration-header">
                <div class="integration-info">
                  <h3 class="integration-name">SimpleFIN</h3>
                  <p class="integration-desc">
                    Connect your bank accounts via SimpleFIN to automatically sync transactions and balances.
                  </p>
                </div>
                {#if isSimplefinConnected}
                  <button class="btn secondary small" onclick={() => openDisconnectConfirm("simplefin")}>
                    Disconnect
                  </button>
                {/if}
              </div>

              {#if isSimplefinConnected && simplefinIntegration}
                <div class="integration-status connected">
                  <span class="status-dot"></span>
                  <span>Connected</span>
                </div>

                <!-- Linked accounts by institution -->
                {#if simplefinAccounts.length > 0}
                  <div class="linked-accounts">
                    <div class="accounts-header">
                      <span class="accounts-title">Linked Accounts ({simplefinAccounts.length})</span>
                      <button
                        class="btn secondary small"
                        onclick={checkConnection}
                        disabled={isCheckingConnection}
                      >
                        {#if isCheckingConnection}
                          Checking...
                        {:else}
                          Check Connection
                        {/if}
                      </button>
                    </div>
                    {#each [...accountsByInstitution] as [institution, accounts]}
                      {@const hasWarning = connectionWarnings.some(w => w.includes(institution))}
                      {@const isCheckedOk = connectionCheckSuccess !== null && !hasWarning}
                      <div class="institution-group" class:has-warning={hasWarning} class:checked-ok={isCheckedOk}>
                        <div class="institution-header">
                          <span class="institution-name">{institution}</span>
                          {#if isCheckingConnection}
                            <span class="institution-status checking">...</span>
                          {:else if connectionCheckSuccess !== null}
                            {#if hasWarning}
                              <span class="institution-status warning" title="Connection may need attention">⚠</span>
                            {:else}
                              <span class="institution-status ok" title="Connected">✓</span>
                            {/if}
                          {/if}
                        </div>
                        <div class="institution-accounts">
                          {#each accounts as account}
                            <div class="account-item">
                              <div class="account-info">
                                <span class="account-name">{account.name}</span>
                                {#if account.account_type}
                                  <span class="account-type">{account.account_type}</span>
                                {/if}
                              </div>
                              <label class="toggle-label" title={account.balances_only ? "Only syncing balances (no transactions)" : "Syncing balances and transactions"}>
                                <input
                                  type="checkbox"
                                  checked={account.balances_only}
                                  onchange={() => toggleBalancesOnly(account)}
                                />
                                <span class="toggle-text">{account.balances_only ? "Balances only" : "Full sync"}</span>
                              </label>
                            </div>
                          {/each}
                        </div>
                      </div>
                    {/each}

                    <!-- Connection warnings -->
                    {#if connectionWarnings.length > 0}
                      <div class="connection-warnings">
                        {#each connectionWarnings as warning}
                          <div class="warning-item">
                            <span class="warning-icon">⚠</span>
                            <span class="warning-text">{warning}</span>
                          </div>
                        {/each}
                        <button
                          class="link-btn"
                          onclick={() => openExternalUrl("https://beta-bridge.simplefin.org/")}
                        >
                          Fix connection issues on SimpleFIN →
                        </button>
                      </div>
                    {/if}
                  </div>
                {:else}
                  <div class="no-accounts">
                    <p>No accounts synced yet. Run a sync to fetch your accounts.</p>
                  </div>
                {/if}

                <div class="integration-details">
                  <div class="detail-row">
                    <span class="detail-label">Connected:</span>
                    <span class="detail-value">{new Date(simplefinIntegration.created_at).toLocaleDateString()}</span>
                  </div>
                  {#if settings?.app.lastSyncDate}
                    <div class="detail-row">
                      <span class="detail-label">Last synced:</span>
                      <span class="detail-value">{formatLastSync(settings.app.lastSyncDate)}</span>
                    </div>
                  {/if}
                </div>

                <div class="simplefin-link">
                  <button
                    class="link-btn"
                    onclick={() => openExternalUrl("https://beta-bridge.simplefin.org/")}
                  >
                    Manage connections on SimpleFIN →
                  </button>
                </div>
              {:else}
                <div class="integration-status disconnected">
                  <span class="status-dot"></span>
                  <span>Not connected</span>
                </div>
                <button class="btn primary" onclick={openSetupModal}>
                  Connect SimpleFIN
                </button>
              {/if}
            </div>

          </section>
        {:else if activeSection === "appearance"}
          <section class="section">
            <h2 class="section-title">Appearance</h2>

            <div class="setting-group">
              <h3 class="group-title">Theme</h3>

              <div class="theme-options">
                <label class="theme-option" class:selected={settings.app.theme === "light"}>
                  <input
                    type="radio"
                    name="theme"
                    value="light"
                    checked={settings.app.theme === "light"}
                    onchange={() => handleThemeChange("light")}
                  />
                  <div class="theme-preview light">
                    <div class="preview-bar"></div>
                    <div class="preview-content"></div>
                  </div>
                  <span class="theme-label">Light</span>
                </label>

                <label class="theme-option" class:selected={settings.app.theme === "dark"}>
                  <input
                    type="radio"
                    name="theme"
                    value="dark"
                    checked={settings.app.theme === "dark"}
                    onchange={() => handleThemeChange("dark")}
                  />
                  <div class="theme-preview dark">
                    <div class="preview-bar"></div>
                    <div class="preview-content"></div>
                  </div>
                  <span class="theme-label">Dark</span>
                </label>

                <label class="theme-option" class:selected={settings.app.theme === "system"}>
                  <input
                    type="radio"
                    name="theme"
                    value="system"
                    checked={settings.app.theme === "system"}
                    onchange={() => handleThemeChange("system")}
                  />
                  <div class="theme-preview system">
                    <div class="preview-bar"></div>
                    <div class="preview-content"></div>
                  </div>
                  <span class="theme-label">System</span>
                </label>
              </div>
            </div>
          </section>
        {:else if activeSection === "about"}
          <section class="section">
            <h2 class="section-title">About</h2>

            <div class="about-content">
              <div class="about-logo">◈</div>
              <div class="about-name">treeline</div>
              <div class="about-tagline">The Obsidian of personal finance</div>

              <div class="about-info">
                <div class="info-row">
                  <span class="info-label">Version:</span>
                  <span class="info-value">0.2.0</span>
                </div>
              </div>

              <div class="about-paths">
                <div class="path-row">
                  <span class="path-label">Database:</span>
                  <span class="path-value">~/.treeline/treeline.duckdb</span>
                </div>
                <div class="path-row">
                  <span class="path-label">Plugins:</span>
                  <span class="path-value">~/.treeline/plugins/</span>
                </div>
                <div class="path-row">
                  <span class="path-label">Taggers:</span>
                  <span class="path-value">~/.treeline/taggers/</span>
                </div>
              </div>

              <div class="about-links">
                <button
                  class="link-btn"
                  onclick={() => openExternalUrl("https://github.com/zack-schrag/treeline-money")}
                >
                  GitHub
                </button>
                <span class="link-separator">•</span>
                <button
                  class="link-btn"
                  onclick={() => openExternalUrl("https://github.com/zack-schrag/treeline-money/issues")}
                >
                  Report Issue
                </button>
              </div>
            </div>
          </section>
        {/if}
      {/if}
    </main>
  </div>
</div>

<!-- SimpleFIN Setup Modal -->
{#if showSetupModal}
  <div class="modal-overlay" onclick={closeSetupModal} role="dialog" tabindex="-1">
    <div class="modal setup-modal" onclick={(e) => e.stopPropagation()} role="document">
      {#if setupSuccess}
        <!-- Success State -->
        <div class="modal-header">
          <span class="modal-title">SimpleFIN Connected</span>
          <button class="close-btn" onclick={closeSetupModal}>×</button>
        </div>
        <div class="modal-body success-body">
          <div class="success-icon">✓</div>
          <h3 class="success-title">SimpleFIN Connected!</h3>
          <p class="success-desc">
            Your bank accounts are now linked. Run a sync to fetch your accounts and transactions.
          </p>
        </div>
        <div class="modal-actions">
          <button class="btn secondary" onclick={closeSetupModal}>Close</button>
          <button class="btn primary" onclick={handleSyncAfterSetup}>Sync Now</button>
        </div>
      {:else if isSettingUp}
        <!-- Loading State -->
        <div class="modal-body loading-body">
          <div class="spinner"></div>
          <p class="loading-text">Connecting to SimpleFIN...</p>
          <p class="loading-hint">This exchanges your token for credentials</p>
        </div>
      {:else}
        <!-- Setup Form -->
        <div class="modal-header">
          <span class="modal-title">Connect SimpleFIN</span>
          <button class="close-btn" onclick={closeSetupModal}>×</button>
        </div>
        <div class="modal-body">
          {#if setupError}
            <div class="setup-error">
              <strong>Connection Failed</strong>
              <p>{setupError}</p>
            </div>
          {/if}

          <div class="setup-steps">
            <div class="step">
              <span class="step-num">1</span>
              <div class="step-content">
                <span>Go to SimpleFIN and create an account:</span>
                <button
                  class="link-btn inline"
                  onclick={() => openExternalUrl("https://beta-bridge.simplefin.org/")}
                >
                  beta-bridge.simplefin.org ↗
                </button>
              </div>
            </div>
            <div class="step">
              <span class="step-num">2</span>
              <span class="step-content">Connect your banks in SimpleFIN's interface</span>
            </div>
            <div class="step">
              <span class="step-num">3</span>
              <span class="step-content">Generate a "Setup Token" and paste it below</span>
            </div>
          </div>

          <div class="token-input-group">
            <label for="setup-token">Setup Token</label>
            <input
              id="setup-token"
              type="text"
              bind:value={setupToken}
              placeholder="aHR0cHM6Ly9iZXRhLWJyaWRnZS5zaW1wbGVmaW4ub3..."
              class="token-input"
            />
            <span class="token-hint">Paste the token from SimpleFIN (starts with aHR0...)</span>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn secondary" onclick={closeSetupModal}>Cancel</button>
          <button class="btn primary" onclick={handleSetupSimplefin} disabled={!setupToken.trim()}>
            Connect
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}

<!-- Disconnect Confirmation Modal -->
{#if showDisconnectConfirm}
  <div class="modal-overlay" onclick={closeDisconnectConfirm} role="dialog" tabindex="-1">
    <div class="modal confirm-modal" onclick={(e) => e.stopPropagation()} role="document">
      <div class="modal-header">
        <span class="modal-title">Disconnect Integration?</span>
        <button class="close-btn" onclick={closeDisconnectConfirm}>×</button>
      </div>
      <div class="modal-body">
        <p>Are you sure you want to disconnect <strong>{disconnectingIntegration}</strong>?</p>
        <p class="confirm-note">Your existing accounts and transactions will remain, but new data won't sync until you reconnect.</p>
      </div>
      <div class="modal-actions">
        <button class="btn secondary" onclick={closeDisconnectConfirm}>Cancel</button>
        <button class="btn danger" onclick={handleDisconnect}>Disconnect</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .settings-view {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
  }

  .header {
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
    background: var(--bg-secondary);
  }

  .title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .settings-content {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .settings-nav {
    width: 180px;
    flex-shrink: 0;
    border-right: 1px solid var(--border-primary);
    background: var(--bg-secondary);
    padding: var(--spacing-md);
  }

  .nav-section {
    margin-bottom: var(--spacing-lg);
  }

  .nav-section-title {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--spacing-sm);
    padding-left: var(--spacing-sm);
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    width: 100%;
    padding: 8px var(--spacing-sm);
    background: transparent;
    border: none;
    border-radius: 4px;
    color: var(--text-secondary);
    font-size: 13px;
    text-align: left;
    cursor: pointer;
    transition: all 0.15s;
  }

  .nav-item:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .nav-item.active {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    font-weight: 500;
  }

  .nav-icon {
    font-size: 14px;
  }

  .settings-main {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-lg) var(--spacing-xl);
  }

  .loading {
    color: var(--text-muted);
    font-size: 13px;
  }

  .section {
    max-width: 600px;
  }

  .section-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-lg) 0;
  }

  .setting-group {
    margin-bottom: var(--spacing-xl);
  }

  .group-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    margin: 0 0 var(--spacing-md) 0;
    padding-bottom: var(--spacing-sm);
    border-bottom: 1px solid var(--border-primary);
  }

  .checkbox-setting {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 13px;
    color: var(--text-primary);
    cursor: pointer;
    margin-bottom: var(--spacing-md);
  }

  .checkbox-setting input {
    width: 16px;
    height: 16px;
    accent-color: var(--accent-primary);
  }

  .setting-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
    font-size: 13px;
  }

  .setting-label {
    color: var(--text-secondary);
  }

  .setting-value {
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    transition: all 0.15s;
  }

  .btn.primary {
    background: var(--accent-primary);
    color: white;
  }

  .btn.primary:hover:not(:disabled) {
    opacity: 0.9;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Theme options */
  .theme-options {
    display: flex;
    gap: var(--spacing-md);
  }

  .theme-option {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
  }

  .theme-option input {
    display: none;
  }

  .theme-preview {
    width: 80px;
    height: 56px;
    border-radius: 6px;
    border: 2px solid var(--border-primary);
    overflow: hidden;
    transition: border-color 0.15s;
  }

  .theme-option.selected .theme-preview {
    border-color: var(--accent-primary);
  }

  .theme-preview.light {
    background: #f5f5f5;
  }

  .theme-preview.light .preview-bar {
    height: 12px;
    background: #e0e0e0;
  }

  .theme-preview.light .preview-content {
    padding: 4px;
  }

  .theme-preview.dark {
    background: #1a1a1a;
  }

  .theme-preview.dark .preview-bar {
    height: 12px;
    background: #2a2a2a;
  }

  .theme-preview.system {
    background: linear-gradient(90deg, #f5f5f5 50%, #1a1a1a 50%);
  }

  .theme-preview.system .preview-bar {
    height: 12px;
    background: linear-gradient(90deg, #e0e0e0 50%, #2a2a2a 50%);
  }

  .theme-label {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .theme-option.selected .theme-label {
    color: var(--text-primary);
    font-weight: 500;
  }

  /* About section */
  .about-content {
    text-align: center;
    padding: var(--spacing-xl) 0;
  }

  .about-logo {
    font-size: 48px;
    color: var(--accent-primary);
    margin-bottom: var(--spacing-sm);
  }

  .about-name {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-xs);
  }

  .about-tagline {
    font-size: 14px;
    color: var(--text-muted);
    margin-bottom: var(--spacing-xl);
  }

  .about-info {
    margin-bottom: var(--spacing-lg);
  }

  .info-row {
    font-size: 13px;
    margin-bottom: var(--spacing-xs);
  }

  .info-label {
    color: var(--text-secondary);
  }

  .info-value {
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .about-paths {
    text-align: left;
    max-width: 400px;
    margin: 0 auto var(--spacing-lg);
    padding: var(--spacing-md);
    background: var(--bg-secondary);
    border-radius: 6px;
    font-size: 12px;
  }

  .path-row {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
  }

  .path-row:last-child {
    margin-bottom: 0;
  }

  .path-label {
    color: var(--text-muted);
    min-width: 80px;
  }

  .path-value {
    color: var(--text-secondary);
    font-family: var(--font-mono);
  }

  .about-links {
    font-size: 13px;
  }

  .about-links a {
    color: var(--accent-primary);
    text-decoration: none;
  }

  .about-links a:hover {
    text-decoration: underline;
  }

  .link-separator {
    color: var(--text-muted);
    margin: 0 var(--spacing-sm);
  }

  /* Integration cards */
  .integration-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
  }

  .integration-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-md);
  }

  .integration-info {
    flex: 1;
  }

  .integration-name {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-xs) 0;
  }

  .integration-desc {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
    line-height: 1.4;
  }

  .integration-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    margin-bottom: var(--spacing-md);
  }

  .integration-status .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .integration-status.connected .status-dot {
    background: var(--accent-success, #22c55e);
  }

  .integration-status.connected {
    color: var(--accent-success, #22c55e);
  }

  .integration-status.disconnected .status-dot {
    background: var(--text-muted);
  }

  .integration-status.disconnected {
    color: var(--text-muted);
  }

  .integration-details {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 12px;
  }

  .detail-row {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
  }

  .detail-row:last-child {
    margin-bottom: 0;
  }

  .detail-label {
    color: var(--text-muted);
  }

  .detail-value {
    color: var(--text-primary);
  }

  /* Buttons */
  .btn.secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
  }

  .btn.secondary:hover:not(:disabled) {
    background: var(--bg-secondary);
    border-color: var(--text-muted);
  }

  .btn.small {
    padding: 4px 10px;
    font-size: 12px;
  }

  .btn.danger {
    background: var(--text-negative, #ef4444);
    color: white;
  }

  .btn.danger:hover:not(:disabled) {
    opacity: 0.9;
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 12px;
    width: 90%;
    max-width: 480px;
    max-height: 90vh;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
  }

  .modal-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .close-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 20px;
    cursor: pointer;
    border-radius: 4px;
  }

  .close-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .modal-body {
    padding: var(--spacing-lg);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    padding: var(--spacing-md) var(--spacing-lg);
    border-top: 1px solid var(--border-primary);
    background: var(--bg-secondary);
  }

  /* Setup modal specific */
  .setup-error {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 6px;
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
    color: var(--text-negative, #ef4444);
    font-size: 13px;
  }

  .setup-error strong {
    display: block;
    margin-bottom: var(--spacing-xs);
  }

  .setup-error p {
    margin: 0;
    opacity: 0.9;
  }

  .setup-steps {
    margin-bottom: var(--spacing-lg);
  }

  .step {
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .step:last-child {
    margin-bottom: 0;
  }

  .step-num {
    width: 24px;
    height: 24px;
    background: var(--bg-tertiary);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    flex-shrink: 0;
  }

  .step-content {
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.5;
    padding-top: 2px;
  }

  .token-input-group {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    padding: var(--spacing-md);
  }

  .token-input-group label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }

  .token-input {
    width: 100%;
    padding: 10px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 13px;
    font-family: var(--font-mono);
  }

  .token-input:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .token-hint {
    display: block;
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 6px;
  }

  /* Loading state */
  .loading-body {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--spacing-xl) var(--spacing-lg);
    gap: var(--spacing-md);
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--border-primary);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .loading-text {
    font-size: 14px;
    color: var(--text-primary);
    margin: 0;
  }

  .loading-hint {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0;
  }

  /* Success state */
  .success-body {
    text-align: center;
    padding: var(--spacing-xl) var(--spacing-lg);
  }

  .success-icon {
    width: 56px;
    height: 56px;
    background: var(--accent-success, #22c55e);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    font-weight: bold;
    margin: 0 auto var(--spacing-md);
  }

  .success-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-sm) 0;
  }

  .success-desc {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
    line-height: 1.5;
  }

  /* Confirm modal */
  .confirm-modal .modal-body p {
    margin: 0 0 var(--spacing-sm) 0;
    font-size: 14px;
    color: var(--text-primary);
  }

  .confirm-note {
    font-size: 13px;
    color: var(--text-muted);
  }

  /* Connection warnings */
  .connection-warnings {
    background: rgba(239, 180, 68, 0.1);
    border: 1px solid rgba(239, 180, 68, 0.3);
    border-radius: 6px;
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .warning-item {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);
  }

  .warning-item:last-of-type {
    margin-bottom: var(--spacing-md);
  }

  .warning-icon {
    color: #efb444;
    flex-shrink: 0;
  }

  .warning-text {
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.4;
  }

  /* Linked accounts */
  .linked-accounts {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .accounts-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);
  }

  .accounts-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .institution-group {
    margin-bottom: var(--spacing-md);
  }

  .institution-group:last-child {
    margin-bottom: var(--spacing-md);
  }

  .institution-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
  }

  .institution-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .institution-status {
    font-size: 12px;
    font-weight: 600;
  }

  .institution-status.checking {
    color: var(--text-muted);
  }

  .institution-status.ok {
    color: var(--accent-success, #22c55e);
  }

  .institution-status.warning {
    color: #efb444;
  }

  .institution-accounts {
    padding-left: var(--spacing-sm);
    border-left: 2px solid var(--border-primary);
    transition: border-color 0.2s;
  }

  .institution-group.checked-ok .institution-accounts {
    border-left-color: var(--accent-success, #22c55e);
  }

  .institution-group.has-warning .institution-accounts {
    border-left-color: #efb444;
  }

  .account-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 13px;
    gap: var(--spacing-sm);
  }

  .account-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex: 1;
    min-width: 0;
  }

  .account-name {
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .account-type {
    font-size: 11px;
    color: var(--text-muted);
    background: var(--bg-secondary);
    padding: 2px 6px;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .toggle-label {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    flex-shrink: 0;
  }

  .toggle-label input[type="checkbox"] {
    width: 14px;
    height: 14px;
    cursor: pointer;
    accent-color: var(--accent-primary);
  }

  .toggle-text {
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .no-accounts {
    text-align: center;
    padding: var(--spacing-md);
    color: var(--text-muted);
    font-size: 13px;
  }

  .no-accounts p {
    margin: 0;
  }

  .simplefin-link {
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--border-primary);
  }

  /* Link button - looks like a link but is a button for Tauri opener */
  .link-btn {
    background: none;
    border: none;
    padding: 0;
    font-size: 13px;
    color: var(--accent-primary);
    cursor: pointer;
    text-decoration: none;
  }

  .link-btn:hover {
    text-decoration: underline;
  }

  .link-btn.inline {
    display: block;
    margin-top: 4px;
  }
</style>
