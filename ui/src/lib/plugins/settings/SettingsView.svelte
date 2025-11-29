<script lang="ts">
  import { onMount } from "svelte";
  import {
    getSettings,
    setAppSetting,
    runSync,
    toast,
    themeManager,
    type Settings,
    type AppSettings,
  } from "../../sdk";

  // State
  let settings = $state<Settings | null>(null);
  let isLoading = $state(true);
  let isSyncing = $state(false);

  // Active section
  type Section = "appearance" | "data" | "about";
  let activeSection = $state<Section>("data");

  // Sections config
  const sections: { id: Section; label: string; icon: string }[] = [
    { id: "data", label: "Data", icon: "📊" },
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

  onMount(() => {
    loadSettings();
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
                <a
                  href="https://github.com/zack-schrag/treeline-money"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub
                </a>
                <span class="link-separator">•</span>
                <a
                  href="https://github.com/zack-schrag/treeline-money/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Report Issue
                </a>
              </div>
            </div>
          </section>
        {/if}
      {/if}
    </main>
  </div>
</div>

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
</style>
