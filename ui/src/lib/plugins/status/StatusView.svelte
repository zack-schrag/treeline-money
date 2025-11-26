<script lang="ts">
  import { onMount } from "svelte";
  import { getStatus, type StatusResponse } from "../../sdk";

  let status = $state<StatusResponse | null>(null);
  let isLoading = $state(true);
  let error = $state<string | null>(null);

  async function loadStatus() {
    isLoading = true;
    error = null;

    try {
      status = await getStatus();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load status";
      console.error("Failed to load status:", e);
    } finally {
      isLoading = false;
    }
  }

  onMount(() => {
    loadStatus();
  });
</script>

<div class="status-view">
  {#if isLoading}
    <div class="loading">Loading status...</div>
  {:else if error}
    <div class="error">
      <span class="error-icon">⚠️</span>
      <span class="error-message">{error}</span>
    </div>
  {:else if status}
    <div class="status-content">
      <h1 class="title">Financial Status</h1>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{status.total_accounts}</div>
          <div class="stat-label">Accounts</div>
        </div>

        <div class="stat-card">
          <div class="stat-value">{status.total_transactions}</div>
          <div class="stat-label">Transactions</div>
        </div>

        <div class="stat-card">
          <div class="stat-value">{status.total_snapshots}</div>
          <div class="stat-label">Balance Snapshots</div>
        </div>

        <div class="stat-card">
          <div class="stat-value">{status.total_integrations}</div>
          <div class="stat-label">Integrations</div>
        </div>
      </div>

      {#if status.earliest_date && status.latest_date}
        <div class="date-range">
          <span class="label">Transaction Date Range:</span>
          <span class="dates">{status.earliest_date} to {status.latest_date}</span>
        </div>
      {/if}

      {#if status.integration_names.length > 0}
        <div class="integrations">
          <span class="label">Integrations:</span>
          <span class="names">{status.integration_names.join(", ")}</span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .status-view {
    height: 100%;
    overflow: auto;
    background: var(--bg-primary);
    padding: var(--spacing-xl);
  }

  .loading,
  .error {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 200px;
    color: var(--text-muted);
    font-size: 14px;
  }

  .error {
    flex-direction: column;
    gap: var(--spacing-md);
    color: var(--accent-danger);
  }

  .error-icon {
    font-size: 48px;
  }

  .error-message {
    font-family: var(--font-mono);
    font-size: 13px;
  }

  .status-content {
    max-width: 1200px;
    margin: 0 auto;
  }

  .title {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-xl);
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
  }

  .stat-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    align-items: center;
    text-align: center;
  }

  .stat-value {
    font-family: var(--font-mono);
    font-size: 36px;
    font-weight: 700;
    color: var(--accent-primary);
  }

  .stat-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .date-range,
  .integrations {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    padding: var(--spacing-md) var(--spacing-lg);
    margin-bottom: var(--spacing-md);
    font-size: 13px;
  }

  .label {
    font-weight: 600;
    color: var(--text-secondary);
    margin-right: var(--spacing-sm);
  }

  .dates,
  .names {
    font-family: var(--font-mono);
    color: var(--text-primary);
  }
</style>
