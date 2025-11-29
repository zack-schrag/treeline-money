<script lang="ts">
  import { onMount } from "svelte";
  import Shell from "./lib/core/Shell.svelte";
  import { initializePlugins } from "./lib/plugins";
  import { themeManager, isSyncNeeded, runSync, toast, getAppSetting } from "./lib/sdk";

  let isLoading = $state(true);
  let loadingStatus = $state("Initializing...");

  onMount(async () => {
    try {
      // Initialize theme from settings
      loadingStatus = "Loading theme...";
      const savedTheme = await getAppSetting("theme");
      themeManager.setTheme(savedTheme === "system" ? "dark" : savedTheme);

      // Load all plugins
      loadingStatus = "Loading plugins...";
      await initializePlugins();

      isLoading = false;

      // Check if sync is needed (after UI is loaded so user sees the app)
      checkAndRunSync();
    } catch (error) {
      console.error("Initialization error:", error);
      loadingStatus = `Error: ${error}`;
    }
  });

  async function checkAndRunSync() {
    try {
      const needsSync = await isSyncNeeded();
      if (needsSync) {
        toast.info("Syncing...", "Fetching latest data from integrations");

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

          // Check for errors
          const errors = result.results.filter((r) => r.error);
          if (errors.length > 0) {
            toast.warning(
              "Sync completed with warnings",
              errors.map((e) => e.error).join(", ")
            );
          } else if (totalTransactions > 0 || totalAccounts > 0) {
            toast.success(
              "Sync complete",
              `${totalAccounts} accounts, ${totalTransactions} new transactions`
            );
          }
          // Don't show toast if nothing synced (no integrations configured)
        } catch (e) {
          // Don't show error toast on startup for missing integrations
          console.log("Startup sync skipped:", e);
        }
      }
    } catch (e) {
      console.error("Failed to check sync status:", e);
    }
  }
</script>

{#if isLoading}
  <div class="loading-screen">
    <div class="loading-content">
      <span class="loading-logo">◈</span>
      <span class="loading-text">treeline</span>
      <span class="loading-status">{loadingStatus}</span>
    </div>
  </div>
{:else}
  <Shell />
{/if}

<style>
  .loading-screen {
    width: 100vw;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-primary);
  }

  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);
  }

  .loading-logo {
    font-size: 48px;
    color: var(--accent-primary);
    animation: pulse 2s ease-in-out infinite;
  }

  .loading-text {
    font-family: var(--font-mono);
    font-size: 18px;
    color: var(--text-secondary);
    letter-spacing: -0.5px;
  }

  .loading-status {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-muted);
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }
</style>
