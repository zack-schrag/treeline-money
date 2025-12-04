<script lang="ts">
  import { onMount } from "svelte";
  import Shell from "./lib/core/Shell.svelte";
  import WelcomeModal from "./lib/core/WelcomeModal.svelte";
  import { initializePlugins } from "./lib/plugins";
  import { themeManager, isSyncNeeded, runSync, toast, getAppSetting, registry, activityStore } from "./lib/sdk";

  let isLoading = $state(true);
  let loadingStatus = $state("Initializing...");
  let showWelcome = $state(false);
  let openSettingsAfterWelcome = $state(false);

  onMount(async () => {
    try {
      // Initialize theme from settings
      loadingStatus = "Loading theme...";
      const savedTheme = await getAppSetting("theme");
      themeManager.setTheme(savedTheme === "system" ? "dark" : savedTheme);

      // Check if first-time user
      loadingStatus = "Checking setup...";
      const hasCompletedOnboarding = await getAppSetting("hasCompletedOnboarding");

      // Load all plugins
      loadingStatus = "Loading plugins...";
      await initializePlugins();

      isLoading = false;

      // Show welcome modal for first-time users
      if (!hasCompletedOnboarding) {
        showWelcome = true;
      } else {
        // Check if sync is needed (after UI is loaded so user sees the app)
        checkAndRunSync();
      }
    } catch (error) {
      console.error("Initialization error:", error);
      loadingStatus = `Error: ${error}`;
    }
  });

  function handleWelcomeComplete(openSettings: boolean = false) {
    showWelcome = false;
    if (openSettings) {
      // Use a small delay to ensure Shell is rendered, then open settings
      openSettingsAfterWelcome = true;
      setTimeout(() => {
        registry.executeCommand("core:settings");
        openSettingsAfterWelcome = false;
      }, 100);
    } else {
      // Demo mode was enabled, data was synced by enableDemo()
      // Emit refresh to update views
      registry.emit("data:refresh");
    }
  }

  async function checkAndRunSync() {
    try {
      const needsSync = await isSyncNeeded();
      if (needsSync) {
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
        } finally {
          stopActivity();
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
  {#if showWelcome}
    <WelcomeModal onComplete={handleWelcomeComplete} />
  {/if}
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
