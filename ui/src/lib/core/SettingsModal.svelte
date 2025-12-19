<script lang="ts">
  import { onMount } from "svelte";
  import { openUrl } from "@tauri-apps/plugin-opener";
  import { getVersion } from "@tauri-apps/api/app";
  import { Icon, SUPPORTED_CURRENCIES, DEFAULT_CURRENCY, setCurrency } from "../shared";
  import {
    getSettings,
    setAppSetting,
    runSync,
    executeQuery,
    setupSimplefin,
    getIntegrationSettings,
    updateIntegrationAccountSetting,
    getDisabledPlugins,
    enablePlugin,
    disablePlugin,
    getDemoMode,
    disableDemo,
    installPlugin,
    uninstallPlugin,
    getEncryptionStatus,
    enableEncryption,
    disableEncryption,
    registry,
    toast,
    themeManager,
    activityStore,
    type Settings,
    type AppSettings,
    type EncryptionStatus,
  } from "../sdk";
  import { invoke } from "@tauri-apps/api/core";
  import { getCorePluginManifests } from "../plugins";
  import { checkForUpdate, downloadAndInstall, restartApp, subscribeToUpdates, type UpdateState } from "../sdk/updater";
  import { marked } from "marked";

  interface Props {
    isOpen: boolean;
    onClose: () => void;
  }

  let { isOpen, onClose }: Props = $props();

  // State
  let settings = $state<Settings | null>(null);
  let isLoading = $state(true);
  let isSyncing = $state(false);
  let appVersion = $state<string>("...");

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
    simplefin_id: string;
    name: string;
    institution_name: string;
    account_type: string | null;
    balances_only: boolean;
  }
  let simplefinAccounts = $state<SimplefinAccount[]>([]);
  let connectionWarnings = $state<string[]>([]);
  let isCheckingConnection = $state(false);
  let connectionCheckSuccess = $state<boolean | null>(null);
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

  // Plugin state
  interface PluginInfo {
    id: string;
    name: string;
    description: string;
    enabled: boolean;
  }
  let plugins = $state<PluginInfo[]>([]);
  let pluginsNeedReload = $state(false);

  // Community plugins state
  interface CommunityPluginInfo {
    id: string;
    name: string;
    description: string;
    author: string;
    repo: string;
  }
  interface InstalledPluginInfo {
    id: string;
    name: string;
    version: string;
    description: string;
    author: string;
  }
  let communityPlugins = $state<CommunityPluginInfo[]>([]);
  let installedCommunityPlugins = $state<InstalledPluginInfo[]>([]);
  let isLoadingCommunityPlugins = $state(false);
  let installingPluginId = $state<string | null>(null);
  let uninstallingPluginId = $state<string | null>(null);

  // Plugin detail modal state
  interface PluginDetail {
    id: string;
    name: string;
    description: string;
    author: string;
    repo: string;
    version?: string;
    installed: boolean;
  }
  let selectedPlugin = $state<PluginDetail | null>(null);
  let pluginReadme = $state<string | null>(null);
  let isLoadingReadme = $state(false);

  // Uninstall confirmation state
  interface UninstallConfirmation {
    plugin: InstalledPluginInfo;
    tablesToDelete: string[];
    dependentPlugins: { pluginId: string; pluginName: string; tables: string[] }[];
  }
  let uninstallConfirmation = $state<UninstallConfirmation | null>(null);
  let deletePluginData = $state(true);

  // Install confirmation state
  interface InstallConfirmation {
    plugin: CommunityPluginInfo;
    permissions: {
      read?: string[];
      write?: string[];
      create?: string[];
    };
  }
  let installConfirmation = $state<InstallConfirmation | null>(null);
  let loadingManifestPluginId = $state<string | null>(null);

  // Demo mode state
  let isDemoMode = $state(false);
  let isExitingDemo = $state(false);

  // Update check state
  let isCheckingForUpdate = $state(false);
  let lastUpdateCheckResult = $state<string | null>(null);
  let updateState = $state<UpdateState>({
    available: false,
    version: null,
    notes: null,
    isDownloading: false,
    downloadProgress: 0,
    error: null,
  });
  let isInstallingUpdate = $state(false);
  let isRestartingApp = $state(false);

  // Currency state
  let currentCurrency = $state<string>(DEFAULT_CURRENCY);

  // Active section
  type Section = "data" | "security" | "plugins" | "integrations" | "appearance" | "about";
  let activeSection = $state<Section>("data");

  const sections: { id: Section; label: string; icon: string }[] = [
    { id: "data", label: "Data", icon: "database" },
    { id: "security", label: "Security", icon: "lock" },
    { id: "plugins", label: "Plugins", icon: "zap" },
    { id: "integrations", label: "Integrations", icon: "link" },
    { id: "appearance", label: "Appearance", icon: "palette" },
    { id: "about", label: "About", icon: "info" },
  ];

  // Encryption state
  let encryptionStatus = $state<EncryptionStatus | null>(null);
  let isLoadingEncryption = $state(false);
  let showEncryptModal = $state(false);
  let showDecryptModal = $state(false);
  let encryptPassword = $state("");
  let encryptPasswordConfirm = $state("");
  let decryptPassword = $state("");
  let isEncrypting = $state(false);
  let isDecrypting = $state(false);
  let encryptError = $state("");

  async function loadSettings() {
    isLoading = true;
    try {
      settings = await getSettings();
      isDemoMode = await getDemoMode();
      // Load currency preference
      currentCurrency = settings?.app?.currency || DEFAULT_CURRENCY;
      // Load encryption status
      await loadEncryptionStatus();
    } catch (e) {
      console.error("Failed to load settings:", e);
    } finally {
      isLoading = false;
    }
  }

  async function loadEncryptionStatus() {
    isLoadingEncryption = true;
    try {
      encryptionStatus = await getEncryptionStatus();
    } catch (e) {
      console.error("Failed to load encryption status:", e);
    } finally {
      isLoadingEncryption = false;
    }
  }

  function openEncryptModal() {
    encryptPassword = "";
    encryptPasswordConfirm = "";
    encryptError = "";
    showEncryptModal = true;
  }

  function closeEncryptModal() {
    showEncryptModal = false;
    encryptPassword = "";
    encryptPasswordConfirm = "";
    encryptError = "";
  }

  async function handleEnableEncryption() {
    if (encryptPassword.length < 8) {
      encryptError = "Password must be at least 8 characters";
      return;
    }
    if (encryptPassword !== encryptPasswordConfirm) {
      encryptError = "Passwords do not match";
      return;
    }

    isEncrypting = true;
    encryptError = "";
    try {
      await enableEncryption(encryptPassword);
      toast.success("Encryption enabled", "Your database is now encrypted");
      closeEncryptModal();
      await loadEncryptionStatus();
    } catch (e) {
      encryptError = e instanceof Error ? e.message : String(e);
    } finally {
      isEncrypting = false;
    }
  }

  function openDecryptModal() {
    decryptPassword = "";
    encryptError = "";
    showDecryptModal = true;
  }

  function closeDecryptModal() {
    showDecryptModal = false;
    decryptPassword = "";
    encryptError = "";
  }

  async function handleDisableEncryption() {
    isDecrypting = true;
    encryptError = "";
    try {
      await disableEncryption(decryptPassword);
      toast.success("Encryption disabled", "Your database is no longer encrypted");
      closeDecryptModal();
      await loadEncryptionStatus();
    } catch (e) {
      encryptError = e instanceof Error ? e.message : String(e);
    } finally {
      isDecrypting = false;
    }
  }

  async function handleExitDemoMode() {
    isExitingDemo = true;
    try {
      toast.info("Exiting demo mode...", "Switching to real data");
      await disableDemo();
      isDemoMode = false;
      toast.success("Demo mode disabled", "Now using your real data");
      registry.emit("data:refresh");
      // Reload integrations since we're now in real mode
      await loadIntegrations();
    } catch (e) {
      toast.error("Failed to exit demo mode", e instanceof Error ? e.message : String(e));
    } finally {
      isExitingDemo = false;
    }
  }

  async function loadIntegrations() {
    isLoadingIntegrations = true;
    try {
      const result = await executeQuery(
        "SELECT integration_name, created_at, updated_at FROM sys_integrations"
      );
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

  async function loadPlugins() {
    try {
      const manifests = getCorePluginManifests();
      const disabled = await getDisabledPlugins();
      // Filter out the settings plugin - it can't be disabled
      plugins = manifests
        .filter(m => m.id !== "settings")
        .map(m => ({
          id: m.id,
          name: m.name,
          description: m.description,
          enabled: !disabled.includes(m.id),
        }));
    } catch (e) {
      console.error("Failed to load plugins:", e);
    }
  }

  async function togglePlugin(pluginId: string, enabled: boolean) {
    try {
      if (enabled) {
        await enablePlugin(pluginId);
      } else {
        await disablePlugin(pluginId);
      }
      // Update local state
      plugins = plugins.map(p =>
        p.id === pluginId ? { ...p, enabled } : p
      );
      pluginsNeedReload = true;
    } catch (e) {
      console.error("Failed to toggle plugin:", e);
      toast.error("Failed to update plugin", e instanceof Error ? e.message : String(e));
    }
  }

  // Community plugins URL - fetches from main repo
  const COMMUNITY_PLUGINS_URL = "https://raw.githubusercontent.com/zack-schrag/treeline-money/refs/heads/main/community-plugins.json";

  async function loadCommunityPlugins() {
    isLoadingCommunityPlugins = true;
    try {
      // Fetch registry from GitHub
      const response = await fetch(COMMUNITY_PLUGINS_URL);
      if (!response.ok) throw new Error("Failed to fetch community plugins");
      const data = await response.json();
      communityPlugins = data.plugins || [];

      // Get installed external plugins
      const installed = await invoke<Array<{ manifest: InstalledPluginInfo; path: string }>>("discover_plugins");
      installedCommunityPlugins = installed.map(p => ({
        id: p.manifest.id,
        name: p.manifest.name,
        version: p.manifest.version,
        description: p.manifest.description,
        author: p.manifest.author,
      }));
    } catch (e) {
      console.error("Failed to load community plugins:", e);
      communityPlugins = [];
      installedCommunityPlugins = [];
    } finally {
      isLoadingCommunityPlugins = false;
    }
  }

  /**
   * Fetch manifest from GitHub to get permissions before install.
   * Uses Tauri backend to avoid CORS restrictions.
   */
  async function fetchPluginManifest(repo: string): Promise<{ read?: string[]; write?: string[]; create?: string[] } | null> {
    try {
      const resultStr = await invoke<string>("fetch_plugin_manifest", { url: repo });
      const result = JSON.parse(resultStr);

      if (!result.success) {
        console.error("Failed to fetch manifest:", result.error);
        return null;
      }

      return result.manifest?.permissions?.tables || {};
    } catch (e) {
      console.error("Failed to fetch plugin manifest:", e);
      return null;
    }
  }

  /**
   * Show install confirmation with permissions.
   */
  async function showInstallConfirmation(plugin: CommunityPluginInfo) {
    loadingManifestPluginId = plugin.id;
    try {
      const permissions = await fetchPluginManifest(plugin.repo);
      if (permissions) {
        installConfirmation = {
          plugin,
          permissions,
        };
      } else {
        // Can't fetch permissions, install directly
        await executeInstallPlugin(plugin);
      }
    } catch (e) {
      // If we can't fetch permissions, install directly
      await executeInstallPlugin(plugin);
    } finally {
      loadingManifestPluginId = null;
    }
  }

  /**
   * Cancel install confirmation.
   */
  function cancelInstall() {
    installConfirmation = null;
  }

  /**
   * Execute the actual plugin install.
   */
  async function executeInstallPlugin(plugin: CommunityPluginInfo) {
    installingPluginId = plugin.id;
    installConfirmation = null;
    try {
      const result = await installPlugin(plugin.repo);
      if (result.success) {
        toast.success("Plugin installed", `${result.plugin_name} ${result.version} installed`);
        pluginsNeedReload = true;
        await loadCommunityPlugins();
      } else {
        throw new Error(result.error || "Unknown error");
      }
    } catch (e) {
      toast.error("Failed to install plugin", e instanceof Error ? e.message : String(e));
    } finally {
      installingPluginId = null;
    }
  }

  /**
   * Handle install button click - shows confirmation with permissions.
   */
  async function handleInstallPlugin(plugin: CommunityPluginInfo) {
    await showInstallConfirmation(plugin);
  }

  /**
   * Find plugins that depend on tables being deleted.
   */
  function findDependentPlugins(tablesToDelete: string[], excludePluginId: string): { pluginId: string; pluginName: string; tables: string[] }[] {
    const dependent: { pluginId: string; pluginName: string; tables: string[] }[] = [];
    const allPermissions = registry.getAllPluginPermissions();

    for (const [pluginId, permissions] of allPermissions) {
      if (pluginId === excludePluginId) continue;

      const readTables = permissions.read || [];
      const overlappingTables = readTables.filter(t =>
        tablesToDelete.some(d => d.toLowerCase() === t.toLowerCase())
      );

      if (overlappingTables.length > 0) {
        // Find the plugin name
        const installedPlugin = installedCommunityPlugins.find(p => p.id === pluginId);
        const corePlugin = plugins.find(p => p.id === pluginId);
        const pluginName = installedPlugin?.name || corePlugin?.name || pluginId;

        dependent.push({ pluginId, pluginName, tables: overlappingTables });
      }
    }

    return dependent;
  }

  /**
   * Show uninstall confirmation dialog with table cleanup options.
   */
  function showUninstallConfirmation(plugin: InstalledPluginInfo) {
    // Get the plugin's create tables from registry
    const permissions = registry.getPluginPermissions(plugin.id);
    const tablesToDelete = permissions.create || [];

    // Find dependent plugins
    const dependentPlugins = findDependentPlugins(tablesToDelete, plugin.id);

    uninstallConfirmation = {
      plugin,
      tablesToDelete,
      dependentPlugins,
    };
    deletePluginData = true;
  }

  /**
   * Cancel uninstall confirmation.
   */
  function cancelUninstall() {
    uninstallConfirmation = null;
    deletePluginData = true;
  }

  /**
   * Confirm and execute plugin uninstall.
   */
  async function confirmUninstall() {
    if (!uninstallConfirmation) return;

    const plugin = uninstallConfirmation.plugin;
    const tablesToDrop = deletePluginData ? uninstallConfirmation.tablesToDelete : [];

    uninstallingPluginId = plugin.id;
    uninstallConfirmation = null;

    try {
      // Drop plugin tables if requested
      if (tablesToDrop.length > 0) {
        for (const table of tablesToDrop) {
          try {
            await executeQuery(`DROP TABLE IF EXISTS ${table}`, { readonly: false });
          } catch (e) {
            console.warn(`Failed to drop table ${table}:`, e);
          }
        }
      }

      await uninstallPlugin(plugin.id);
      const dataMsg = tablesToDrop.length > 0 ? " and its data" : "";
      toast.success("Plugin uninstalled", `${plugin.name}${dataMsg} has been removed`);
      pluginsNeedReload = true;
      await loadCommunityPlugins();
    } catch (e) {
      toast.error("Failed to uninstall plugin", e instanceof Error ? e.message : String(e));
    } finally {
      uninstallingPluginId = null;
    }
  }

  /**
   * Handle uninstall - shows confirmation dialog.
   */
  async function handleUninstallPlugin(plugin: InstalledPluginInfo) {
    showUninstallConfirmation(plugin);
  }

  // Check if a community plugin is installed
  function isPluginInstalled(pluginId: string): boolean {
    return installedCommunityPlugins.some(p => p.id === pluginId);
  }

  // Get installed version of a plugin
  function getInstalledVersion(pluginId: string): string | null {
    const installed = installedCommunityPlugins.find(p => p.id === pluginId);
    return installed?.version || null;
  }

  // Open plugin detail modal
  function openPluginDetail(plugin: CommunityPluginInfo | InstalledPluginInfo, fromRegistry: boolean) {
    const installed = isPluginInstalled(plugin.id);
    const version = getInstalledVersion(plugin.id) || (plugin as InstalledPluginInfo).version;

    selectedPlugin = {
      id: plugin.id,
      name: plugin.name,
      description: plugin.description,
      author: plugin.author,
      repo: fromRegistry ? (plugin as CommunityPluginInfo).repo : "",
      version: version || undefined,
      installed,
    };

    // Find repo URL if not from registry
    if (!fromRegistry) {
      const registryPlugin = communityPlugins.find(p => p.id === plugin.id);
      if (registryPlugin) {
        selectedPlugin.repo = registryPlugin.repo;
      }
    }

    pluginReadme = null;
    if (selectedPlugin.repo) {
      fetchPluginReadme(selectedPlugin.repo);
    }
  }

  function closePluginDetail() {
    selectedPlugin = null;
    pluginReadme = null;
  }

  // Fetch README from GitHub
  async function fetchPluginReadme(repoUrl: string) {
    isLoadingReadme = true;
    try {
      // Parse repo URL: https://github.com/owner/repo -> owner/repo
      const match = repoUrl.match(/github\.com\/([^/]+\/[^/]+)/);
      if (!match) {
        pluginReadme = null;
        return;
      }

      const repoPath = match[1];
      const response = await fetch(`https://api.github.com/repos/${repoPath}/readme`, {
        headers: { Accept: "application/vnd.github.v3+json" },
      });

      if (!response.ok) {
        pluginReadme = null;
        return;
      }

      const data = await response.json();
      // README is base64 encoded
      pluginReadme = atob(data.content);
    } catch (e) {
      console.error("Failed to fetch README:", e);
      pluginReadme = null;
    } finally {
      isLoadingReadme = false;
    }
  }

  let isSimplefinConnected = $derived(
    integrations.some((i) => i.integration_name === "simplefin")
  );

  let simplefinIntegration = $derived(
    integrations.find((i) => i.integration_name === "simplefin")
  );

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
      account.balances_only = newValue;
      simplefinAccounts = [...simplefinAccounts];
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

  function openSetupModalFn() {
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
    themeManager.setTheme(theme === "system" ? "dark" : theme);
  }

  async function handleCurrencyChange(currency: string) {
    if (!settings) return;
    await setAppSetting("currency", currency);
    currentCurrency = currency;
    setCurrency(currency); // Update the reactive store
    if (settings.app) {
      settings.app.currency = currency;
    }
    // Refresh data to update currency formatting across the app
    registry.emit("data:refresh");
    toast.success("Currency updated", `Your currency is now ${SUPPORTED_CURRENCIES[currency]?.name || currency}`);
  }

  async function handleAutoSyncChange(enabled: boolean) {
    if (!settings) return;
    await setAppSetting("autoSyncOnStartup", enabled);
    settings.app.autoSyncOnStartup = enabled;
  }

  async function handleAutoUpdateChange(enabled: boolean) {
    if (!settings) return;
    await setAppSetting("autoUpdate", enabled);
    settings.app.autoUpdate = enabled;
  }

  async function handleCheckForUpdate() {
    isCheckingForUpdate = true;
    lastUpdateCheckResult = null;
    try {
      const update = await checkForUpdate(true);
      if (update) {
        lastUpdateCheckResult = `Update available: v${update.version}`;
        // Don't show toast - we'll show inline UI instead
      } else {
        lastUpdateCheckResult = "You're up to date!";
        toast.info("No updates", "You're running the latest version");
      }
    } catch (e) {
      lastUpdateCheckResult = "Failed to check for updates";
      toast.error("Update check failed", e instanceof Error ? e.message : String(e));
    } finally {
      isCheckingForUpdate = false;
    }
  }

  async function handleInstallUpdate() {
    isInstallingUpdate = true;
    try {
      await downloadAndInstall();
      // After download, updateState will be updated via subscription
    } catch (e) {
      toast.error("Update failed", e instanceof Error ? e.message : String(e));
    } finally {
      isInstallingUpdate = false;
    }
  }

  async function handleRestartApp() {
    isRestartingApp = true;
    try {
      await restartApp();
    } catch (e) {
      toast.error("Restart failed", e instanceof Error ? e.message : String(e));
      isRestartingApp = false;
    }
  }

  // Check if update is ready to install (downloaded)
  let isUpdateReadyToInstall = $derived(updateState.downloadProgress === 100 && !updateState.isDownloading);

  async function handleSync() {
    isSyncing = true;
    const stopActivity = activityStore.start("Syncing accounts...");
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

      await loadSettings();
    } catch (e) {
      toast.error("Sync failed", e instanceof Error ? e.message : String(e));
    } finally {
      stopActivity();
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

  function handleOverlayClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      onClose();
    }
  }

  // Load data when modal opens
  $effect(() => {
    if (isOpen) {
      pluginsNeedReload = false; // Reset on open
      lastUpdateCheckResult = null; // Reset update check result
      loadSettings();
      loadPlugins();
      loadCommunityPlugins();
      loadIntegrations().then(() => {
        if (integrations.some((i) => i.integration_name === "simplefin")) {
          loadSimplefinAccounts();
        }
      });
      getVersion().then((v) => (appVersion = v));

      // Subscribe to update state
      const unsubscribe = subscribeToUpdates((state) => {
        updateState = state;
      });

      return () => {
        unsubscribe();
      };
    }
  });
</script>

{#if isOpen}
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="settings-overlay"
    onclick={handleOverlayClick}
    onkeydown={handleKeyDown}
    role="dialog"
    aria-modal="true"
    aria-labelledby="settings-title"
    tabindex="-1"
  >
    <div class="settings-modal">
      <!-- Header -->
      <div class="modal-header">
        <h2 id="settings-title" class="modal-title">Settings</h2>
        <button class="close-btn" onclick={onClose} aria-label="Close settings">
          <Icon name="x" size={18} />
        </button>
      </div>

      <div class="settings-content">
        <!-- Sidebar navigation -->
        <nav class="settings-nav">
          {#each sections as section}
            <button
              class="nav-item"
              class:active={activeSection === section.id}
              onclick={() => (activeSection = section.id)}
            >
              <Icon name={section.icon} size={16} />
              <span class="nav-label">{section.label}</span>
            </button>
          {/each}
        </nav>

        <!-- Main content area -->
        <main class="settings-main">
          {#if isLoading}
            <div class="loading">Loading settings...</div>
          {:else if settings}
            {#if activeSection === "data"}
              <section class="section">
                <h3 class="section-title">Data</h3>

                <div class="setting-group">
                  <h4 class="group-title">Sync</h4>

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
                      <Icon name="refresh" size={14} class="spinning" />
                      Syncing...
                    {:else}
                      <Icon name="refresh" size={14} />
                      Sync Now
                    {/if}
                  </button>
                </div>

                <div class="setting-group">
                  <h4 class="group-title">Currency</h4>
                  <p class="group-desc">Choose the currency for displaying amounts throughout the app. All your accounts should be in this currency.</p>

                  <div class="currency-select-wrapper">
                    <select
                      class="currency-select"
                      value={currentCurrency}
                      onchange={(e) => handleCurrencyChange(e.currentTarget.value)}
                    >
                      {#each Object.entries(SUPPORTED_CURRENCIES) as [code, info]}
                        <option value={code}>{info.symbol} {info.name} ({code})</option>
                      {/each}
                    </select>
                  </div>
                </div>

                <div class="setting-group">
                  <h4 class="group-title">Updates</h4>

                  <label class="checkbox-setting">
                    <input
                      type="checkbox"
                      checked={settings.app.autoUpdate}
                      onchange={(e) => handleAutoUpdateChange(e.currentTarget.checked)}
                    />
                    <span>Automatically check for updates</span>
                  </label>
                  <p class="group-desc">When enabled, Treeline will check for updates on startup and every 24 hours. You'll be notified when an update is available.</p>

                  {#if updateState.available || updateState.isDownloading || isUpdateReadyToInstall}
                    <!-- Update available - show inline update UI -->
                    <div class="update-card">
                      {#if isUpdateReadyToInstall}
                        <div class="update-card-content">
                          <Icon name="check-circle" size={20} class="update-icon success" />
                          <div class="update-info">
                            <strong>Update ready!</strong>
                            <span>Treeline v{updateState.version} has been downloaded. Restart to apply.</span>
                          </div>
                        </div>
                        <button
                          class="btn primary"
                          onclick={handleRestartApp}
                          disabled={isRestartingApp}
                        >
                          {isRestartingApp ? "Restarting..." : "Restart Now"}
                        </button>
                      {:else if updateState.isDownloading}
                        <div class="update-card-content">
                          <Icon name="download" size={20} class="update-icon" />
                          <div class="update-info">
                            <strong>Downloading update...</strong>
                            <span>v{updateState.version} — {updateState.downloadProgress}%</span>
                          </div>
                        </div>
                        <div class="update-progress">
                          <div class="update-progress-fill" style="width: {updateState.downloadProgress}%"></div>
                        </div>
                      {:else}
                        <div class="update-card-content">
                          <Icon name="arrow-up-circle" size={20} class="update-icon" />
                          <div class="update-info">
                            <strong>Update available</strong>
                            <span>Treeline v{updateState.version} is ready to download</span>
                          </div>
                        </div>
                        <button
                          class="btn primary"
                          onclick={handleInstallUpdate}
                          disabled={isInstallingUpdate}
                        >
                          {isInstallingUpdate ? "Starting..." : "Download & Install"}
                        </button>
                      {/if}
                    </div>
                  {:else}
                    <!-- No update - show check button -->
                    <button
                      class="btn secondary"
                      onclick={handleCheckForUpdate}
                      disabled={isCheckingForUpdate}
                    >
                      {#if isCheckingForUpdate}
                        <Icon name="refresh" size={14} class="spinning" />
                        Checking...
                      {:else}
                        <Icon name="refresh" size={14} />
                        Check for Updates
                      {/if}
                    </button>
                    {#if lastUpdateCheckResult}
                      <p class="update-result">{lastUpdateCheckResult}</p>
                    {/if}
                  {/if}
                </div>
              </section>
            {:else if activeSection === "security"}
              <section class="section">
                <h3 class="section-title">Security</h3>

                {#if isDemoMode}
                  <div class="demo-warning">
                    <Icon name="alert-triangle" size={16} />
                    <span>Encryption is not available in demo mode</span>
                  </div>
                {:else if isLoadingEncryption}
                  <div class="loading">Loading encryption status...</div>
                {:else}
                  <div class="setting-group">
                    <h4 class="group-title">Database Encryption</h4>

                    <div class="encryption-status">
                      <div class="status-row">
                        <span class="status-label">Status:</span>
                        <span class="status-value" class:encrypted={encryptionStatus?.encrypted}>
                          {#if encryptionStatus?.encrypted}
                            <Icon name="lock" size={14} />
                            Encrypted
                          {:else}
                            <Icon name="unlock" size={14} />
                            Not encrypted
                          {/if}
                        </span>
                      </div>
                      {#if encryptionStatus?.encrypted}
                        <div class="status-row">
                          <span class="status-label">Algorithm:</span>
                          <span class="status-value">{encryptionStatus.algorithm || "Unknown"}</span>
                        </div>
                      {/if}
                    </div>

                    <p class="setting-description">
                      Encrypt your database to protect your financial data at rest.
                      Uses AES-256-GCM encryption with Argon2id key derivation.
                    </p>

                    <div class="encryption-actions">
                      {#if encryptionStatus?.encrypted}
                        <button class="btn danger" onclick={openDecryptModal}>
                          <Icon name="unlock" size={14} />
                          Disable Encryption
                        </button>
                      {:else}
                        <button class="btn primary" onclick={openEncryptModal}>
                          <Icon name="lock" size={14} />
                          Enable Encryption
                        </button>
                      {/if}
                    </div>

                    {#if encryptionStatus?.encrypted}
                      <p class="encryption-hint">
                        You'll need to enter your password each time you open the app.
                      </p>
                    {:else}
                      <p class="encryption-hint">
                        After enabling encryption, you'll need to enter your password
                        each time you open the app.
                      </p>
                    {/if}
                  </div>
                {/if}
              </section>
            {:else if activeSection === "plugins"}
              <section class="section">
                <h3 class="section-title">Plugins</h3>

                {#if pluginsNeedReload}
                  <div class="reload-notice">
                    <Icon name="info" size={14} />
                    <span>Restart the app to apply plugin changes</span>
                  </div>
                {/if}

                <div class="setting-group">
                  <h4 class="group-title">Core Plugins</h4>
                  <p class="group-desc">Enable or disable built-in functionality. Disabled plugins won't appear in the sidebar.</p>

                  <div class="plugin-list">
                    {#each plugins as plugin}
                      <div class="plugin-item">
                        <div class="plugin-info">
                          <span class="plugin-name">{plugin.name}</span>
                          <span class="plugin-desc">{plugin.description}</span>
                        </div>
                        <label class="toggle-switch">
                          <input
                            type="checkbox"
                            checked={plugin.enabled}
                            onchange={() => togglePlugin(plugin.id, !plugin.enabled)}
                          />
                          <span class="toggle-slider"></span>
                        </label>
                      </div>
                    {/each}
                  </div>
                </div>

                <div class="setting-group">
                  <h4 class="group-title">Community Plugins</h4>
                  <p class="group-desc">Browse and install plugins created by the community.</p>

                  {#if isLoadingCommunityPlugins}
                    <div class="loading-placeholder">Loading community plugins...</div>
                  {:else if communityPlugins.length === 0 && installedCommunityPlugins.length === 0}
                    <div class="empty-state">
                      <p>No community plugins available yet.</p>
                    </div>
                  {:else}
                    <div class="plugin-list">
                      {#each communityPlugins as plugin}
                        {@const installed = isPluginInstalled(plugin.id)}
                        {@const installedVersion = getInstalledVersion(plugin.id)}
                        <div class="plugin-item community clickable" onclick={() => openPluginDetail(plugin, true)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && openPluginDetail(plugin, true)}>
                          <div class="plugin-info">
                            <div class="plugin-header">
                              <span class="plugin-name">{plugin.name}</span>
                              {#if installed && installedVersion}
                                <span class="plugin-version">v{installedVersion}</span>
                              {/if}
                            </div>
                            <span class="plugin-desc">{plugin.description}</span>
                            <span class="plugin-author">by {plugin.author}</span>
                          </div>
                          <div class="plugin-actions" onclick={(e) => e.stopPropagation()}>
                            {#if installed}
                              <button
                                class="btn secondary small"
                                onclick={() => {
                                  const p = installedCommunityPlugins.find(ip => ip.id === plugin.id);
                                  if (p) handleUninstallPlugin(p);
                                }}
                                disabled={uninstallingPluginId === plugin.id}
                              >
                                {uninstallingPluginId === plugin.id ? "Removing..." : "Remove"}
                              </button>
                            {:else}
                              <button
                                class="btn primary small"
                                onclick={() => handleInstallPlugin(plugin)}
                                disabled={installingPluginId === plugin.id || loadingManifestPluginId === plugin.id}
                              >
                                {#if installingPluginId === plugin.id}
                                  Installing...
                                {:else if loadingManifestPluginId === plugin.id}
                                  Loading...
                                {:else}
                                  Install
                                {/if}
                              </button>
                            {/if}
                          </div>
                        </div>
                      {/each}

                      {#each installedCommunityPlugins.filter(p => !communityPlugins.some(cp => cp.id === p.id)) as plugin}
                        <div class="plugin-item community installed-only clickable" onclick={() => openPluginDetail(plugin, false)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && openPluginDetail(plugin, false)}>
                          <div class="plugin-info">
                            <div class="plugin-header">
                              <span class="plugin-name">{plugin.name}</span>
                              <span class="plugin-version">v{plugin.version}</span>
                            </div>
                            <span class="plugin-desc">{plugin.description}</span>
                            {#if plugin.author}
                              <span class="plugin-author">by {plugin.author}</span>
                            {/if}
                          </div>
                          <div class="plugin-actions" onclick={(e) => e.stopPropagation()}>
                            <button
                              class="btn secondary small"
                              onclick={() => handleUninstallPlugin(plugin)}
                              disabled={uninstallingPluginId === plugin.id}
                            >
                              {uninstallingPluginId === plugin.id ? "Removing..." : "Remove"}
                            </button>
                          </div>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              </section>
            {:else if activeSection === "integrations"}
              <section class="section">
                <h3 class="section-title">Integrations</h3>

                {#if isDemoMode}
                  <div class="demo-mode-notice">
                    <div class="notice-icon"><Icon name="beaker" size={24} /></div>
                    <div class="notice-content">
                      <h4>Demo Mode Active</h4>
                      <p>Integration setup is disabled while in demo mode to prevent mixing real data with sample data.</p>
                      <button
                        class="btn primary"
                        onclick={handleExitDemoMode}
                        disabled={isExitingDemo}
                      >
                        {isExitingDemo ? "Exiting..." : "Exit Demo Mode"}
                      </button>
                    </div>
                  </div>
                {:else}
                <div class="integration-card">
                  <div class="integration-header">
                    <div class="integration-info">
                      <h4 class="integration-name">SimpleFIN</h4>
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
                        <div class="sync-settings-help">
                          <Icon name="info" size={14} />
                          <span class="help-text">Choose what to sync for each account. Select "Balances only" for accounts where you don't need individual transactions.</span>
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
                                  <span class="institution-status warning">!</span>
                                {:else}
                                  <Icon name="check" size={12} class="status-ok" />
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
                                  <div class="segmented-toggle">
                                    <button
                                      class="toggle-option"
                                      class:active={!account.balances_only}
                                      onclick={() => { if (account.balances_only) toggleBalancesOnly(account); }}
                                    >
                                      Balances + Transactions
                                    </button>
                                    <button
                                      class="toggle-option"
                                      class:active={account.balances_only}
                                      onclick={() => { if (!account.balances_only) toggleBalancesOnly(account); }}
                                    >
                                      Balances only
                                    </button>
                                  </div>
                                </div>
                              {/each}
                            </div>
                          </div>
                        {/each}

                        {#if connectionWarnings.length > 0}
                          <div class="connection-warnings">
                            {#each connectionWarnings as warning}
                              <div class="warning-item">
                                <span class="warning-icon">!</span>
                                <span class="warning-text">{warning}</span>
                              </div>
                            {/each}
                            <button
                              class="link-btn"
                              onclick={() => openExternalUrl("https://beta-bridge.simplefin.org/")}
                            >
                              Fix connection issues on SimpleFIN
                              <Icon name="external-link" size={12} />
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
                        Manage connections on SimpleFIN
                        <Icon name="external-link" size={12} />
                      </button>
                    </div>
                  {:else}
                    <div class="integration-status disconnected">
                      <span class="status-dot"></span>
                      <span>Not connected</span>
                    </div>
                    <button class="btn primary" onclick={openSetupModalFn}>
                      Connect SimpleFIN
                    </button>
                  {/if}
                </div>
                {/if}
              </section>
            {:else if activeSection === "appearance"}
              <section class="section">
                <h3 class="section-title">Appearance</h3>

                <div class="setting-group">
                  <h4 class="group-title">Theme</h4>

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
                <h3 class="section-title">About</h3>

                <div class="about-content">
                  <div class="about-logo">◈</div>
                  <div class="about-name">treeline</div>
                  <div class="about-tagline">The Obsidian of personal finance</div>

                  <div class="about-info">
                    <div class="info-row">
                      <span class="info-label">Version:</span>
                      <span class="info-value">{appVersion}</span>
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
                  </div>

                  <div class="about-links">
                    <button
                      class="link-btn"
                      onclick={() => openExternalUrl("https://github.com/zack-schrag/treeline-money")}
                    >
                      GitHub
                    </button>
                    <span class="link-separator">·</span>
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
  </div>

  <!-- SimpleFIN Setup Sub-Modal -->
  {#if showSetupModal}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="sub-modal-overlay" onclick={closeSetupModal} onkeydown={(e) => e.key === 'Escape' && closeSetupModal()} role="dialog" aria-modal="true" tabindex="-1">
      <div class="sub-modal" role="document">
        {#if setupSuccess}
          <div class="sub-modal-header">
            <span class="sub-modal-title">SimpleFIN Connected</span>
            <button class="close-btn" onclick={closeSetupModal}>
              <Icon name="x" size={16} />
            </button>
          </div>
          <div class="sub-modal-body success-body">
            <div class="success-icon">
              <Icon name="check" size={28} />
            </div>
            <h3 class="success-title">SimpleFIN Connected!</h3>
            <p class="success-desc">
              Your bank accounts are now linked. Run a sync to fetch your accounts and transactions.
            </p>
          </div>
          <div class="sub-modal-actions">
            <button class="btn secondary" onclick={closeSetupModal}>Close</button>
            <button class="btn primary" onclick={handleSyncAfterSetup}>Sync Now</button>
          </div>
        {:else if isSettingUp}
          <div class="sub-modal-body loading-body">
            <div class="spinner"></div>
            <p class="loading-text">Connecting to SimpleFIN...</p>
            <p class="loading-hint">This exchanges your token for credentials</p>
          </div>
        {:else}
          <div class="sub-modal-header">
            <span class="sub-modal-title">Connect SimpleFIN</span>
            <button class="close-btn" onclick={closeSetupModal}>
              <Icon name="x" size={16} />
            </button>
          </div>
          <div class="sub-modal-body">
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
                    beta-bridge.simplefin.org
                    <Icon name="external-link" size={12} />
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
          <div class="sub-modal-actions">
            <button class="btn secondary" onclick={closeSetupModal}>Cancel</button>
            <button class="btn primary" onclick={handleSetupSimplefin} disabled={!setupToken.trim()}>
              Connect
            </button>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Disconnect Confirmation Sub-Modal -->
  {#if showDisconnectConfirm}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="sub-modal-overlay" onclick={closeDisconnectConfirm} onkeydown={(e) => e.key === 'Escape' && closeDisconnectConfirm()} role="dialog" aria-modal="true" tabindex="-1">
      <div class="sub-modal confirm-modal" role="document">
        <div class="sub-modal-header">
          <span class="sub-modal-title">Disconnect Integration?</span>
          <button class="close-btn" onclick={closeDisconnectConfirm}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <div class="sub-modal-body">
          <p>Are you sure you want to disconnect <strong>{disconnectingIntegration}</strong>?</p>
          <p class="confirm-note">Your existing accounts and transactions will remain, but new data won't sync until you reconnect.</p>
        </div>
        <div class="sub-modal-actions">
          <button class="btn secondary" onclick={closeDisconnectConfirm}>Cancel</button>
          <button class="btn danger" onclick={handleDisconnect}>Disconnect</button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Enable Encryption Sub-Modal -->
  {#if showEncryptModal}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="sub-modal-overlay" onclick={closeEncryptModal} onkeydown={(e) => e.key === 'Escape' && closeEncryptModal()} role="dialog" aria-modal="true" tabindex="-1">
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="sub-modal" role="document" onclick={(e) => e.stopPropagation()}>
        <div class="sub-modal-header">
          <span class="sub-modal-title">Enable Encryption</span>
          <button class="close-btn" onclick={closeEncryptModal}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <div class="sub-modal-body">
          <p class="encrypt-warning">
            Choose a strong password. If you forget it, your data cannot be recovered.
          </p>

          {#if encryptError}
            <div class="encrypt-error">{encryptError}</div>
          {/if}

          <div class="form-group">
            <label for="encrypt-password">Password</label>
            <input
              id="encrypt-password"
              type="password"
              bind:value={encryptPassword}
              placeholder="Enter password (min 8 characters)"
              disabled={isEncrypting}
            />
          </div>

          <div class="form-group">
            <label for="encrypt-password-confirm">Confirm Password</label>
            <input
              id="encrypt-password-confirm"
              type="password"
              bind:value={encryptPasswordConfirm}
              placeholder="Confirm password"
              disabled={isEncrypting}
            />
          </div>
        </div>
        <div class="sub-modal-actions">
          <button class="btn secondary" onclick={closeEncryptModal} disabled={isEncrypting}>Cancel</button>
          <button class="btn primary" onclick={handleEnableEncryption} disabled={isEncrypting || encryptPassword.length < 8 || encryptPassword !== encryptPasswordConfirm}>
            {#if isEncrypting}
              Encrypting...
            {:else}
              Enable Encryption
            {/if}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Disable Encryption Sub-Modal -->
  {#if showDecryptModal}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="sub-modal-overlay" onclick={closeDecryptModal} onkeydown={(e) => e.key === 'Escape' && closeDecryptModal()} role="dialog" aria-modal="true" tabindex="-1">
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="sub-modal" role="document" onclick={(e) => e.stopPropagation()}>
        <div class="sub-modal-header">
          <span class="sub-modal-title">Disable Encryption</span>
          <button class="close-btn" onclick={closeDecryptModal}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <div class="sub-modal-body">
          <p class="encrypt-warning">
            Enter your current password to disable encryption.
            Your data will be stored unencrypted.
          </p>

          {#if encryptError}
            <div class="encrypt-error">{encryptError}</div>
          {/if}

          <div class="form-group">
            <label for="decrypt-password">Current Password</label>
            <input
              id="decrypt-password"
              type="password"
              bind:value={decryptPassword}
              placeholder="Enter current password"
              disabled={isDecrypting}
            />
          </div>
        </div>
        <div class="sub-modal-actions">
          <button class="btn secondary" onclick={closeDecryptModal} disabled={isDecrypting}>Cancel</button>
          <button class="btn danger" onclick={handleDisableEncryption} disabled={isDecrypting || !decryptPassword}>
            {#if isDecrypting}
              Decrypting...
            {:else}
              Disable Encryption
            {/if}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Plugin Detail Modal -->
  {#if selectedPlugin}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="sub-modal-overlay plugin-detail-overlay" onclick={closePluginDetail} onkeydown={(e) => e.key === 'Escape' && closePluginDetail()} role="dialog" aria-modal="true" tabindex="-1">
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="sub-modal plugin-detail-modal" onclick={(e) => e.stopPropagation()} role="document">
        <div class="sub-modal-header">
          <span class="sub-modal-title">{selectedPlugin.name}</span>
          <button class="close-btn" onclick={closePluginDetail}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <div class="sub-modal-body plugin-detail-body">
          <div class="plugin-detail-meta">
            {#if selectedPlugin.version}
              <span class="plugin-detail-version">v{selectedPlugin.version}</span>
            {/if}
            <span class="plugin-detail-author">by {selectedPlugin.author}</span>
            {#if selectedPlugin.installed}
              <span class="plugin-detail-badge installed">Installed</span>
            {/if}
          </div>
          <p class="plugin-detail-desc">{selectedPlugin.description}</p>

          {#if selectedPlugin.repo}
            <button class="link-btn repo-link" onclick={() => openUrl(selectedPlugin!.repo)}>
              <Icon name="external-link" size={14} />
              View on GitHub
            </button>
          {/if}

          {#if isLoadingReadme}
            <div class="readme-loading">
              <div class="loading-spinner"></div>
              <span>Loading README...</span>
            </div>
          {:else if pluginReadme}
            <div class="plugin-readme">
              <h4 class="readme-title">README</h4>
              <div class="readme-content">{@html marked(pluginReadme)}</div>
            </div>
          {/if}
        </div>
        <div class="sub-modal-actions">
          {#if selectedPlugin.installed}
            <button
              class="btn secondary"
              onclick={() => {
                const p = installedCommunityPlugins.find(ip => ip.id === selectedPlugin!.id);
                if (p) {
                  handleUninstallPlugin(p);
                  closePluginDetail();
                }
              }}
              disabled={uninstallingPluginId === selectedPlugin.id}
            >
              {uninstallingPluginId === selectedPlugin.id ? "Removing..." : "Remove Plugin"}
            </button>
          {:else}
            <button
              class="btn primary"
              onclick={() => {
                const p = communityPlugins.find(cp => cp.id === selectedPlugin!.id);
                if (p) {
                  closePluginDetail();
                  handleInstallPlugin(p);
                }
              }}
              disabled={installingPluginId === selectedPlugin.id || loadingManifestPluginId === selectedPlugin.id}
            >
              {#if installingPluginId === selectedPlugin.id}
                Installing...
              {:else if loadingManifestPluginId === selectedPlugin.id}
                Loading...
              {:else}
                Install Plugin
              {/if}
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}

  <!-- Uninstall Confirmation Modal -->
  {#if uninstallConfirmation}
    <div class="sub-modal-overlay" onclick={cancelUninstall} role="presentation">
      <div class="sub-modal uninstall-confirm-modal" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && cancelUninstall()} role="dialog" tabindex="-1">
        <div class="sub-modal-header">
          <h3>Remove {uninstallConfirmation.plugin.name}?</h3>
          <button class="close-btn" onclick={cancelUninstall}>✕</button>
        </div>
        <div class="sub-modal-content">
          {#if uninstallConfirmation.tablesToDelete.length > 0}
            <div class="uninstall-option">
              <label class="checkbox-label">
                <input type="checkbox" bind:checked={deletePluginData} />
                <span>Also delete plugin data</span>
              </label>
              <div class="tables-list">
                <span class="tables-label">Tables:</span>
                {#each uninstallConfirmation.tablesToDelete as table}
                  <code class="table-name">{table}</code>
                {/each}
              </div>
            </div>

            {#if deletePluginData && uninstallConfirmation.dependentPlugins.length > 0}
              <div class="dependency-warning">
                <div class="warning-header">
                  <Icon name="alert-triangle" size={16} />
                  <span>Warning: Other plugins depend on this data</span>
                </div>
                <ul class="dependent-list">
                  {#each uninstallConfirmation.dependentPlugins as dep}
                    <li>
                      <strong>{dep.pluginName}</strong> reads: {dep.tables.join(", ")}
                    </li>
                  {/each}
                </ul>
                <p class="warning-note">Deleting this data may break these plugins.</p>
              </div>
            {/if}
          {:else}
            <p class="no-data-note">This plugin has no data to delete.</p>
          {/if}
        </div>
        <div class="sub-modal-actions">
          <button class="btn secondary" onclick={cancelUninstall}>Cancel</button>
          <button
            class="btn danger"
            onclick={confirmUninstall}
            disabled={uninstallingPluginId === uninstallConfirmation.plugin.id}
          >
            {uninstallingPluginId === uninstallConfirmation.plugin.id ? "Removing..." : "Remove"}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Install Confirmation Modal -->
  {#if installConfirmation}
    <div class="sub-modal-overlay" onclick={cancelInstall} role="presentation">
      <div class="sub-modal install-confirm-modal" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && cancelInstall()} role="dialog" tabindex="-1">
        <div class="sub-modal-header">
          <h3>Install {installConfirmation.plugin.name}?</h3>
          <button class="close-btn" onclick={cancelInstall}>✕</button>
        </div>
        <div class="sub-modal-content">
          <p class="install-desc">{installConfirmation.plugin.description}</p>
          <p class="install-author">by {installConfirmation.plugin.author}</p>

          <div class="permissions-section">
            <h4 class="permissions-title">Permissions</h4>

            {#if installConfirmation.permissions.read?.length}
              <div class="permission-group">
                <span class="permission-label">Can read:</span>
                <div class="permission-tables">
                  {#each installConfirmation.permissions.read as table}
                    <code class="table-name">{table === "*" ? "all tables" : table}</code>
                  {/each}
                </div>
              </div>
            {/if}

            {#if installConfirmation.permissions.write?.length}
              <div class="permission-group">
                <span class="permission-label">Can write:</span>
                <div class="permission-tables">
                  {#each installConfirmation.permissions.write as table}
                    <code class="table-name">{table}</code>
                  {/each}
                </div>
              </div>
            {/if}

            {#if installConfirmation.permissions.create?.length}
              <div class="permission-group">
                <span class="permission-label">Creates tables:</span>
                <div class="permission-tables">
                  {#each installConfirmation.permissions.create as table}
                    <code class="table-name">{table}</code>
                  {/each}
                </div>
              </div>
            {/if}

            {#if !installConfirmation.permissions.read?.length && !installConfirmation.permissions.write?.length && !installConfirmation.permissions.create?.length}
              <p class="no-permissions">No special permissions required.</p>
            {/if}
          </div>
        </div>
        <div class="sub-modal-actions">
          <button class="btn secondary" onclick={cancelInstall}>Cancel</button>
          <button
            class="btn primary"
            onclick={() => executeInstallPlugin(installConfirmation!.plugin)}
            disabled={installingPluginId === installConfirmation.plugin.id}
          >
            {installingPluginId === installConfirmation.plugin.id ? "Installing..." : "Install"}
          </button>
        </div>
      </div>
    </div>
  {/if}
{/if}

<style>
  .settings-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(2px);
  }

  .settings-modal {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 12px;
    width: 90%;
    max-width: 720px;
    height: 80%;
    max-height: 600px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
    background: var(--bg-secondary);
  }

  .modal-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
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
    cursor: pointer;
    border-radius: 4px;
  }

  .close-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .settings-content {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .settings-nav {
    width: 160px;
    flex-shrink: 0;
    border-right: 1px solid var(--border-primary);
    background: var(--bg-secondary);
    padding: var(--spacing-sm);
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    width: 100%;
    padding: 8px 12px;
    background: transparent;
    border: none;
    border-radius: 6px;
    color: var(--text-secondary);
    font-size: 13px;
    text-align: left;
    cursor: pointer;
    transition: all 0.15s;
    margin-bottom: 2px;
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

  .settings-main {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-lg);
  }

  .loading {
    color: var(--text-muted);
    font-size: 13px;
  }

  .section {
    max-width: 480px;
  }

  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-lg) 0;
  }

  .setting-group {
    margin-bottom: var(--spacing-xl);
  }

  .group-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
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
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border-radius: 6px;
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

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  :global(.spinning) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
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
    width: 72px;
    height: 48px;
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
    height: 10px;
    background: #e0e0e0;
  }

  .theme-preview.dark {
    background: #1a1a1a;
  }

  .theme-preview.dark .preview-bar {
    height: 10px;
    background: #2a2a2a;
  }

  .theme-preview.system {
    background: linear-gradient(90deg, #f5f5f5 50%, #1a1a1a 50%);
  }

  .theme-preview.system .preview-bar {
    height: 10px;
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
    padding: var(--spacing-lg) 0;
  }

  .about-logo {
    font-size: 40px;
    color: var(--accent-primary);
    margin-bottom: var(--spacing-xs);
  }

  .about-name {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .about-tagline {
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: var(--spacing-lg);
  }

  .about-info {
    margin-bottom: var(--spacing-md);
  }

  .info-row {
    font-size: 13px;
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
    max-width: 320px;
    margin: 0 auto var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-secondary);
    border-radius: 6px;
    font-size: 11px;
  }

  .path-row {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: 4px;
  }

  .path-row:last-child {
    margin-bottom: 0;
  }

  .path-label {
    color: var(--text-muted);
    min-width: 70px;
  }

  .path-value {
    color: var(--text-secondary);
    font-family: var(--font-mono);
  }

  .about-links {
    font-size: 13px;
  }

  .link-separator {
    color: var(--text-muted);
    margin: 0 var(--spacing-sm);
  }

  /* Demo mode notice */
  .demo-mode-notice {
    display: flex;
    gap: var(--spacing-md);
    padding: var(--spacing-lg);
    background: linear-gradient(135deg, rgba(180, 83, 9, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%);
    border: 1px solid rgba(217, 119, 6, 0.3);
    border-radius: 8px;
  }

  .demo-mode-notice .notice-icon {
    display: flex;
    align-items: flex-start;
    flex-shrink: 0;
    color: #d97706;
  }

  .demo-mode-notice .notice-content h4 {
    margin: 0 0 var(--spacing-xs) 0;
    font-size: 14px;
    font-weight: 600;
    color: #d97706;
  }

  .demo-mode-notice .notice-content p {
    margin: 0 0 var(--spacing-md) 0;
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  /* Integration cards */
  .integration-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    padding: var(--spacing-md);
  }

  .integration-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-sm);
  }

  .integration-info {
    flex: 1;
  }

  .integration-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 4px 0;
  }

  .integration-desc {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0;
    line-height: 1.4;
  }

  .integration-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
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
    font-size: 11px;
  }

  .detail-row {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: 4px;
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

  /* Linked accounts */
  .linked-accounts {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: var(--spacing-sm) var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .accounts-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-sm);
  }

  .accounts-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .sync-settings-help {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--bg-secondary);
    border-radius: 4px;
    margin-bottom: var(--spacing-sm);
  }

  .help-text {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.4;
  }

  .institution-group {
    margin-bottom: var(--spacing-sm);
  }

  .institution-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: 4px;
  }

  .institution-name {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .institution-status {
    font-size: 11px;
    font-weight: 600;
  }

  .institution-status.checking {
    color: var(--text-muted);
  }

  :global(.status-ok) {
    color: var(--accent-success, #22c55e);
  }

  .institution-status.warning {
    color: #efb444;
  }

  .institution-accounts {
    padding-left: var(--spacing-sm);
    border-left: 2px solid var(--border-primary);
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
    padding: 4px var(--spacing-sm);
    font-size: 12px;
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
    font-size: 10px;
    color: var(--text-muted);
    background: var(--bg-secondary);
    padding: 2px 5px;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .segmented-toggle {
    display: flex;
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    overflow: hidden;
    flex-shrink: 0;
  }

  .segmented-toggle .toggle-option {
    background: var(--bg-secondary);
    border: none;
    padding: 3px 8px;
    font-size: 10px;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
  }

  .segmented-toggle .toggle-option:not(:last-child) {
    border-right: 1px solid var(--border-primary);
  }

  .segmented-toggle .toggle-option:hover:not(.active) {
    background: var(--bg-tertiary);
  }

  .segmented-toggle .toggle-option.active {
    background: var(--accent-primary);
    color: white;
  }

  .connection-warnings {
    background: rgba(239, 180, 68, 0.1);
    border: 1px solid rgba(239, 180, 68, 0.3);
    border-radius: 4px;
    padding: var(--spacing-sm);
    margin-top: var(--spacing-sm);
  }

  .warning-item {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
  }

  .warning-icon {
    color: #efb444;
    font-weight: bold;
    flex-shrink: 0;
  }

  .warning-text {
    font-size: 12px;
    color: var(--text-primary);
    line-height: 1.4;
  }

  .no-accounts {
    text-align: center;
    padding: var(--spacing-sm);
    color: var(--text-muted);
    font-size: 12px;
  }

  .no-accounts p {
    margin: 0;
  }

  .simplefin-link {
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-sm);
    border-top: 1px solid var(--border-primary);
  }

  .link-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: none;
    padding: 0;
    font-size: 12px;
    color: var(--accent-primary);
    cursor: pointer;
    text-decoration: none;
  }

  .link-btn:hover {
    text-decoration: underline;
  }

  .link-btn.inline {
    display: flex;
    margin-top: 4px;
  }

  /* Sub-modals (SimpleFIN setup, disconnect confirm) */
  .sub-modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1001;
  }

  .sub-modal {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 10px;
    width: 90%;
    max-width: 420px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    overflow: hidden;
  }

  .sub-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid var(--border-primary);
  }

  .sub-modal-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .sub-modal-body {
    padding: var(--spacing-lg);
  }

  .sub-modal-content {
    padding: var(--spacing-lg);
  }

  .sub-modal-actions {
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
    padding: var(--spacing-sm) var(--spacing-md);
    margin-bottom: var(--spacing-md);
    color: var(--text-negative, #ef4444);
    font-size: 12px;
  }

  .setup-error strong {
    display: block;
    margin-bottom: 4px;
  }

  .setup-error p {
    margin: 0;
    opacity: 0.9;
  }

  .setup-steps {
    margin-bottom: var(--spacing-md);
  }

  .step {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);
  }

  .step:last-child {
    margin-bottom: 0;
  }

  .step-num {
    width: 20px;
    height: 20px;
    background: var(--bg-tertiary);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    flex-shrink: 0;
  }

  .step-content {
    font-size: 12px;
    color: var(--text-primary);
    line-height: 1.5;
    padding-top: 2px;
  }

  .token-input-group {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .token-input-group label {
    display: block;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }

  .token-input {
    width: 100%;
    padding: 8px 10px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 12px;
    font-family: var(--font-mono);
  }

  .token-input:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .token-hint {
    display: block;
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  /* Loading state */
  .loading-body {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--spacing-xl) var(--spacing-lg);
    gap: var(--spacing-sm);
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border-primary);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .loading-text {
    font-size: 13px;
    color: var(--text-primary);
    margin: 0;
  }

  .loading-hint {
    font-size: 11px;
    color: var(--text-muted);
    margin: 0;
  }

  /* Success state */
  .success-body {
    text-align: center;
    padding: var(--spacing-lg);
  }

  .success-icon {
    width: 48px;
    height: 48px;
    background: var(--accent-success, #22c55e);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto var(--spacing-md);
  }

  .success-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-xs) 0;
  }

  .success-desc {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0;
    line-height: 1.5;
  }

  /* Confirm modal */
  .confirm-modal .sub-modal-body p {
    margin: 0 0 var(--spacing-xs) 0;
    font-size: 13px;
    color: var(--text-primary);
  }

  .confirm-note {
    font-size: 12px !important;
    color: var(--text-muted) !important;
  }

  /* Uninstall confirmation modal */
  .uninstall-confirm-modal {
    max-width: 450px;
  }

  .uninstall-option {
    margin-bottom: var(--spacing-md);
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 13px;
    cursor: pointer;
    margin-bottom: var(--spacing-sm);
  }

  .checkbox-label input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--accent-primary);
  }

  .tables-list {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--spacing-xs);
    padding-left: 24px;
  }

  .tables-label {
    font-size: 11px;
    color: var(--text-muted);
  }

  .table-name {
    font-family: var(--font-mono);
    font-size: 11px;
    background: var(--bg-tertiary);
    padding: 4px 8px;
    border-radius: 4px;
    color: var(--text-secondary);
  }

  .dependency-warning {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 6px;
    padding: var(--spacing-md);
    margin-top: var(--spacing-md);
  }

  .warning-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 13px;
    font-weight: 500;
    color: var(--accent-danger);
    margin-bottom: var(--spacing-sm);
  }

  .dependent-list {
    margin: 0 0 var(--spacing-sm) var(--spacing-lg);
    padding: 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .dependent-list li {
    margin-bottom: var(--spacing-xs);
  }

  .warning-note {
    font-size: 11px;
    color: var(--text-muted);
    margin: 0;
  }

  .no-data-note {
    font-size: 13px;
    color: var(--text-secondary);
    margin: 0;
  }

  /* Install confirmation modal */
  .install-confirm-modal {
    max-width: 480px;
  }

  .install-desc {
    font-size: 14px;
    color: var(--text-primary);
    margin: 0;
    line-height: 1.4;
  }

  .install-author {
    font-size: 12px;
    color: var(--text-muted);
    margin: var(--spacing-xs) 0 var(--spacing-lg) 0;
  }

  .permissions-section {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    padding: var(--spacing-md) var(--spacing-lg);
  }

  .permissions-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 var(--spacing-md) 0;
  }

  .permission-group {
    margin-bottom: var(--spacing-md);
  }

  .permission-group:last-child {
    margin-bottom: 0;
  }

  .permission-label {
    display: block;
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: var(--spacing-xs);
  }

  .permission-tables {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .no-permissions {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0;
  }

  /* Plugins section */
  .reload-notice {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(239, 180, 68, 0.15);
    border: 1px solid rgba(239, 180, 68, 0.3);
    border-radius: 6px;
    margin-bottom: var(--spacing-md);
    font-size: 12px;
    color: #efb444;
  }

  .group-desc {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0 0 var(--spacing-md) 0;
    line-height: 1.4;
  }

  .update-result {
    font-size: 12px;
    color: var(--text-secondary);
    margin: var(--spacing-sm) 0 0 0;
  }

  .plugin-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .plugin-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    gap: var(--spacing-md);
  }

  .plugin-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .plugin-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .plugin-desc {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.3;
  }

  /* Toggle switch */
  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 36px;
    height: 20px;
    flex-shrink: 0;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 10px;
    transition: 0.2s;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 14px;
    width: 14px;
    left: 2px;
    bottom: 2px;
    background-color: var(--text-muted);
    border-radius: 50%;
    transition: 0.2s;
  }

  .toggle-switch input:checked + .toggle-slider {
    background-color: var(--accent-primary);
    border-color: var(--accent-primary);
  }

  .toggle-switch input:checked + .toggle-slider:before {
    transform: translateX(16px);
    background-color: white;
  }

  /* Community plugins */
  .loading-placeholder,
  .empty-state {
    color: var(--text-muted);
    font-size: 13px;
    padding: var(--spacing-md);
    text-align: center;
  }

  .empty-state p {
    margin: 0;
  }

  .plugin-item.community {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }

  .plugin-item.community .plugin-info {
    gap: 4px;
  }

  .plugin-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .plugin-version {
    font-size: 11px;
    color: var(--text-muted);
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .plugin-author {
    font-size: 11px;
    color: var(--text-muted);
  }

  .plugin-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
  }

  .plugin-item.installed-only {
    opacity: 0.8;
    border-style: dashed;
  }

  .plugin-item.clickable {
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }

  .plugin-item.clickable:hover {
    background: var(--bg-tertiary);
    border-color: var(--accent-primary);
  }

  .plugin-item.clickable:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  /* Plugin detail modal */
  .plugin-detail-overlay {
    z-index: 1100;
  }

  .plugin-detail-modal {
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
  }

  .plugin-detail-body {
    padding: var(--spacing-lg);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .plugin-detail-meta {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .plugin-detail-version {
    font-size: 12px;
    color: var(--text-muted);
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 4px;
  }

  .plugin-detail-author {
    font-size: 12px;
    color: var(--text-muted);
  }

  .plugin-detail-badge {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 4px;
  }

  .plugin-detail-badge.installed {
    background: var(--accent-success);
    color: white;
  }

  .plugin-detail-desc {
    font-size: 14px;
    color: var(--text-primary);
    line-height: 1.5;
    margin: 0;
  }

  .repo-link {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: 13px;
    color: var(--accent-primary);
  }

  .repo-link:hover {
    text-decoration: underline;
  }

  .readme-loading {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    color: var(--text-muted);
    font-size: 13px;
  }

  .loading-spinner {
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

  .plugin-readme {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    padding: var(--spacing-md);
  }

  .readme-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
    margin: 0 0 var(--spacing-sm) 0;
  }

  .readme-content {
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-secondary);
    max-height: 300px;
    overflow-y: auto;
  }

  .readme-content :global(h1),
  .readme-content :global(h2),
  .readme-content :global(h3),
  .readme-content :global(h4) {
    color: var(--text-primary);
    margin: var(--spacing-md) 0 var(--spacing-sm) 0;
    font-weight: 600;
  }

  .readme-content :global(h1) { font-size: 18px; }
  .readme-content :global(h2) { font-size: 16px; }
  .readme-content :global(h3) { font-size: 14px; }
  .readme-content :global(h4) { font-size: 13px; }

  .readme-content :global(h1:first-child),
  .readme-content :global(h2:first-child),
  .readme-content :global(h3:first-child) {
    margin-top: 0;
  }

  .readme-content :global(p) {
    margin: 0 0 var(--spacing-sm) 0;
  }

  .readme-content :global(ul),
  .readme-content :global(ol) {
    margin: 0 0 var(--spacing-sm) 0;
    padding-left: var(--spacing-lg);
  }

  .readme-content :global(li) {
    margin-bottom: 4px;
  }

  .readme-content :global(code) {
    font-family: var(--font-mono);
    font-size: 12px;
    background: var(--bg-primary);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .readme-content :global(pre) {
    background: var(--bg-primary);
    padding: var(--spacing-sm);
    border-radius: 4px;
    overflow-x: auto;
    margin: 0 0 var(--spacing-sm) 0;
  }

  .readme-content :global(pre code) {
    background: none;
    padding: 0;
  }

  .readme-content :global(a) {
    color: var(--accent-primary);
  }

  .readme-content :global(a:hover) {
    text-decoration: underline;
  }

  /* Encryption/Security styles */
  .encryption-status {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .encryption-status .status-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
  }

  .encryption-status .status-row:last-child {
    margin-bottom: 0;
  }

  .encryption-status .status-label {
    color: var(--text-muted);
    font-size: 12px;
    min-width: 80px;
  }

  .encryption-status .status-value {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .encryption-status .status-value.encrypted {
    color: var(--accent-success, #22c55e);
  }

  .encryption-actions {
    display: flex;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .encryption-actions .btn {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .encryption-hint {
    font-size: 11px;
    color: var(--text-muted);
    margin: 0;
    line-height: 1.5;
  }

  .encrypt-warning {
    color: var(--accent-warning, #f59e0b);
    font-size: 13px;
    margin: 0 0 var(--spacing-md) 0;
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(245, 158, 11, 0.1);
    border-radius: 4px;
  }

  .encrypt-error {
    color: var(--accent-danger, #ef4444);
    font-size: 12px;
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--accent-danger, #ef4444);
    border-radius: 4px;
    margin-bottom: var(--spacing-md);
  }

  .demo-warning {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    color: var(--accent-warning, #f59e0b);
    background: rgba(245, 158, 11, 0.1);
    padding: var(--spacing-md);
    border-radius: 6px;
  }

  /* Update card styles */
  .update-card {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 8px;
    padding: var(--spacing-md);
  }

  .update-card-content {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  :global(.update-icon) {
    color: var(--accent-primary);
    flex-shrink: 0;
    margin-top: 2px;
  }

  :global(.update-icon.success) {
    color: var(--accent-success, #22c55e);
  }

  .update-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .update-info strong {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .update-info span {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .update-progress {
    height: 6px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 3px;
    overflow: hidden;
    margin-top: var(--spacing-sm);
  }

  .update-progress-fill {
    height: 100%;
    background: var(--accent-primary);
    transition: width 0.2s ease;
  }

  /* Currency select */
  .currency-select-wrapper {
    max-width: 280px;
  }

  .currency-select {
    width: 100%;
    padding: 8px 28px 8px 10px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 13px;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    cursor: pointer;
  }

  .currency-select:focus {
    outline: none;
    border-color: var(--accent-primary);
  }

  .currency-select option {
    background: var(--bg-secondary);
    color: var(--text-primary);
    padding: 8px;
  }
</style>
