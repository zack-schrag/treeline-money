<script lang="ts">
  import { onMount } from "svelte";
  import { getVersion } from "@tauri-apps/api/app";
  import { Modal } from "../shared";
  import { getAppSetting, setAppSetting } from "../sdk/settings";

  interface Props {
    onclose: () => void;
  }

  let { onclose }: Props = $props();

  let appVersion = $state<string>("");
  let releaseNotes = $state<string>("");
  let isLoading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      appVersion = await getVersion();
      await fetchReleaseNotes(appVersion);
    } catch (e) {
      console.error("Failed to load release notes:", e);
      error = "Failed to load release notes";
    } finally {
      isLoading = false;
    }
  });

  async function fetchReleaseNotes(version: string) {
    try {
      // Fetch release notes from GitHub API
      const response = await fetch(
        `https://api.github.com/repos/zack-schrag/treeline-money/releases/tags/v${version}`
      );

      if (response.ok) {
        const data = await response.json();
        releaseNotes = data.body || "No release notes available.";
      } else if (response.status === 404) {
        // Version might not have a release yet (dev build)
        releaseNotes = "You're running the latest version!";
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (e) {
      console.error("Failed to fetch release notes:", e);
      releaseNotes = "Unable to fetch release notes. Check your internet connection.";
    }
  }

  async function handleClose() {
    // Mark this version as seen
    await setAppSetting("lastSeenVersion", appVersion);
    onclose();
  }

  // Simple markdown-like rendering (headers and bullets)
  function renderNotes(notes: string): string {
    return notes
      // Convert ## headers to styled divs
      .replace(/^## (.+)$/gm, '<h2 class="notes-title">$1</h2>')
      // Convert ### headers to styled divs
      .replace(/^### (.+)$/gm, '<h3 class="notes-section">$1</h3>')
      // Convert bullet points
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      // Wrap consecutive li elements in ul
      .replace(/(<li>.*<\/li>\n?)+/g, '<ul class="notes-list">$&</ul>')
      // Convert **bold** to strong
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Convert line breaks
      .replace(/\n/g, '');
  }
</script>

<Modal open={true} title="What's New" onclose={handleClose} width="500px">
  <div class="whats-new-content">
    {#if isLoading}
      <div class="loading">
        <span class="spinner"></span>
        <span>Loading release notes...</span>
      </div>
    {:else if error}
      <div class="error">{error}</div>
    {:else}
      <div class="version-badge">v{appVersion}</div>
      <div class="release-notes">
        {@html renderNotes(releaseNotes)}
      </div>
    {/if}
  </div>

  {#snippet actions()}
    <button class="btn primary" onclick={handleClose}>Got it!</button>
  {/snippet}
</Modal>

<style>
  .whats-new-content {
    min-height: 150px;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-md);
    padding: var(--spacing-xl);
    color: var(--text-muted);
  }

  .spinner {
    width: 24px;
    height: 24px;
    border: 2px solid var(--border-primary);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .error {
    padding: var(--spacing-lg);
    color: var(--accent-danger);
    text-align: center;
  }

  .version-badge {
    display: inline-block;
    padding: 4px 12px;
    background: var(--accent-primary);
    color: white;
    font-size: 12px;
    font-weight: 600;
    border-radius: 12px;
    margin-bottom: var(--spacing-md);
  }

  .release-notes {
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-primary);
  }

  .release-notes :global(h2.notes-title) {
    font-size: 18px;
    font-weight: 600;
    margin: 0 0 var(--spacing-md) 0;
    color: var(--text-primary);
  }

  .release-notes :global(h3.notes-section) {
    font-size: 14px;
    font-weight: 600;
    margin: var(--spacing-md) 0 var(--spacing-sm) 0;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .release-notes :global(ul.notes-list) {
    margin: 0 0 var(--spacing-md) 0;
    padding-left: var(--spacing-lg);
  }

  .release-notes :global(li) {
    margin-bottom: var(--spacing-xs);
    color: var(--text-primary);
  }

  .btn {
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn.primary {
    background: var(--accent-primary);
    border: none;
    color: white;
  }

  .btn.primary:hover {
    filter: brightness(1.1);
  }
</style>
