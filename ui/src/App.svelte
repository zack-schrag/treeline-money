<script lang="ts">
  import { onMount } from "svelte";
  import Shell from "./lib/core/Shell.svelte";
  import { initializePlugins } from "./lib/plugins";
  import { themeManager } from "./lib/sdk";

  let isLoading = $state(true);
  let loadingStatus = $state("Initializing...");

  onMount(async () => {
    try {
      // Initialize theme
      loadingStatus = "Loading theme...";
      themeManager.init();

      // Load all plugins
      loadingStatus = "Loading plugins...";
      await initializePlugins();

      isLoading = false;
    } catch (error) {
      console.error("Initialization error:", error);
      loadingStatus = `Error: ${error}`;
    }
  });
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
