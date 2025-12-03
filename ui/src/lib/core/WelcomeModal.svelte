<script lang="ts">
  import { Icon } from "../shared";
  import { enableDemo, setAppSetting, toast } from "../sdk";

  interface Props {
    onComplete: (openSettings?: boolean) => void;
  }

  let { onComplete }: Props = $props();

  let isLoading = $state(false);
  let loadingAction = $state<"demo" | "real" | null>(null);

  async function handleTryDemo() {
    isLoading = true;
    loadingAction = "demo";
    try {
      toast.info("Setting up demo...", "Loading sample data");
      await enableDemo();
      await setAppSetting("hasCompletedOnboarding", true);
      toast.success("Demo mode enabled", "Explore with sample data");
      onComplete(false);
    } catch (e) {
      toast.error("Failed to enable demo", e instanceof Error ? e.message : String(e));
      isLoading = false;
      loadingAction = null;
    }
  }

  async function handleConnectReal() {
    isLoading = true;
    loadingAction = "real";
    try {
      await setAppSetting("hasCompletedOnboarding", true);
      // Open settings to integrations tab
      onComplete(true);
    } catch (e) {
      toast.error("Failed to save settings", e instanceof Error ? e.message : String(e));
      isLoading = false;
      loadingAction = null;
    }
  }
</script>

<div class="welcome-overlay" role="dialog" aria-modal="true" aria-labelledby="welcome-title">
  <div class="welcome-modal">
    <div class="welcome-header">
      <div class="logo">◈</div>
      <h1 id="welcome-title">Welcome to Treeline</h1>
      <p class="tagline">Your personal finance command center</p>
    </div>

    <div class="welcome-content">
      <p class="intro">
        Treeline gives you complete control over your financial data with powerful
        querying, tagging, and visualization tools.
      </p>

      <div class="options">
        <button
          class="option-card"
          onclick={handleTryDemo}
          disabled={isLoading}
        >
          <div class="option-icon">
            <Icon name="beaker" size={28} />
          </div>
          <div class="option-content">
            <h3>Try Demo Mode</h3>
            <p>Explore with sample data. Perfect for getting familiar with the app before connecting your accounts.</p>
          </div>
          {#if loadingAction === "demo"}
            <div class="option-loading">
              <div class="spinner"></div>
            </div>
          {:else}
            <Icon name="arrow-right" size={20} />
          {/if}
        </button>

        <button
          class="option-card"
          onclick={handleConnectReal}
          disabled={isLoading}
        >
          <div class="option-icon">
            <Icon name="link" size={28} />
          </div>
          <div class="option-content">
            <h3>Connect Real Data</h3>
            <p>Link your bank accounts via SimpleFIN to start tracking your actual finances.</p>
          </div>
          {#if loadingAction === "real"}
            <div class="option-loading">
              <div class="spinner"></div>
            </div>
          {:else}
            <Icon name="arrow-right" size={20} />
          {/if}
        </button>
      </div>
    </div>

    <div class="welcome-footer">
      <p>You can switch between demo and real data anytime in Settings.</p>
    </div>
  </div>
</div>

<style>
  .welcome-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    backdrop-filter: blur(4px);
  }

  .welcome-modal {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 16px;
    width: 90%;
    max-width: 520px;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
    overflow: hidden;
  }

  .welcome-header {
    text-align: center;
    padding: var(--spacing-xl) var(--spacing-xl) var(--spacing-lg);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-primary);
  }

  .logo {
    font-size: 48px;
    color: var(--accent-primary);
    margin-bottom: var(--spacing-sm);
  }

  .welcome-header h1 {
    margin: 0 0 var(--spacing-xs) 0;
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .tagline {
    margin: 0;
    font-size: 14px;
    color: var(--text-muted);
  }

  .welcome-content {
    padding: var(--spacing-lg) var(--spacing-xl);
  }

  .intro {
    margin: 0 0 var(--spacing-lg) 0;
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.6;
    text-align: center;
  }

  .options {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .option-card {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
    color: var(--text-primary);
  }

  .option-card:hover:not(:disabled) {
    border-color: var(--accent-primary);
    background: var(--bg-tertiary);
  }

  .option-card:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .option-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    flex-shrink: 0;
    background: var(--bg-tertiary);
    border-radius: 10px;
    color: var(--accent-primary);
  }

  .option-content {
    flex: 1;
    min-width: 0;
  }

  .option-content h3 {
    margin: 0 0 4px 0;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .option-content p {
    margin: 0;
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.4;
  }

  .option-card :global(svg) {
    color: var(--text-muted);
    flex-shrink: 0;
    transition: transform 0.2s ease;
  }

  .option-card:hover:not(:disabled) :global(svg) {
    color: var(--accent-primary);
    transform: translateX(4px);
  }

  .option-loading {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-primary);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .welcome-footer {
    padding: var(--spacing-md) var(--spacing-xl);
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-primary);
    text-align: center;
  }

  .welcome-footer p {
    margin: 0;
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
