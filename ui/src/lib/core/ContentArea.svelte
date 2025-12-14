<script lang="ts">
  import { registry, modKey } from "../sdk";
  import { createPluginSDK } from "../sdk/public";
  import type { Tab, ViewDefinition } from "../sdk";

  let activeTab = $state<Tab | null>(registry.activeTab);
  let views = $state(registry.views);
  let mountContainer = $state<HTMLDivElement | null>(null);
  let cleanup: (() => void) | null = null;

  $effect(() => {
    return registry.subscribe(() => {
      activeTab = registry.activeTab;
      views = registry.views;
    });
  });

  let activeView = $derived.by(() => {
    if (!activeTab) return null;
    return registry.getView(activeTab.viewId) ?? null;
  });

  // Handle mount-based views (for external plugins)
  $effect(() => {
    // Clean up previous mount
    if (cleanup) {
      cleanup();
      cleanup = null;
    }

    // Mount new view if it uses mount API
    if (activeView?.mount && mountContainer && activeTab) {
      // Get plugin ID and permissions for this view
      const pluginId = registry.getPluginIdForView(activeTab.viewId);
      const allowedTables = pluginId ? registry.getPluginWriteTables(pluginId) : [];

      // Create SDK instance for this plugin
      const sdk = pluginId ? createPluginSDK(pluginId, allowedTables) : null;

      // Pass SDK and original props to the view
      const props = {
        ...activeTab.props,
        sdk,
      };

      cleanup = activeView.mount(mountContainer, props);
    }

    // Cleanup on unmount
    return () => {
      if (cleanup) {
        cleanup();
        cleanup = null;
      }
    };
  });
</script>

<main class="content-area">
  {#if activeTab && activeView}
    {#if activeView.component}
      <!-- Core plugin with Svelte component -->
      {@const Component = activeView.component}
      <Component {...activeTab.props} />
    {:else if activeView.mount}
      <!-- External plugin with mount function -->
      <div bind:this={mountContainer} class="plugin-mount-container"></div>
    {/if}
  {:else}
    <div class="empty-state">
      <div class="empty-content">
        <div class="empty-logo">◈</div>
        <h2 class="empty-title">treeline</h2>
        <p class="empty-subtitle">Select a view from the sidebar or press <kbd>{modKey()}P</kbd> to open the command palette</p>

        <div class="keyboard-hints">
          <div class="hint-group">
            <kbd>{modKey()}P</kbd>
            <span>Command palette</span>
          </div>
          <div class="hint-group">
            <kbd>{modKey()}1-9</kbd>
            <span>Switch tabs</span>
          </div>
          <div class="hint-group">
            <kbd>{modKey()}W</kbd>
            <span>Close tab</span>
          </div>
        </div>
      </div>
    </div>
  {/if}
</main>

<style>
  .content-area {
    flex: 1;
    background: var(--bg-primary);
    overflow: auto;
  }

  .empty-state {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .empty-content {
    text-align: center;
    max-width: 400px;
  }

  .empty-logo {
    font-size: 64px;
    color: var(--accent-primary);
    margin-bottom: var(--spacing-lg);
    opacity: 0.5;
  }

  .empty-title {
    font-family: var(--font-mono);
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-sm);
    letter-spacing: -1px;
  }

  .empty-subtitle {
    color: var(--text-secondary);
    font-size: 14px;
    margin: 0 0 var(--spacing-xl);
    line-height: 1.5;
  }

  .keyboard-hints {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    text-align: left;
    background: var(--bg-secondary);
    padding: var(--spacing-lg);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-primary);
  }

  .hint-group {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  kbd {
    font-family: var(--font-mono);
    font-size: 11px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: 2px 8px;
    min-width: 60px;
    text-align: center;
    color: var(--text-secondary);
  }

  .hint-group span {
    color: var(--text-secondary);
    font-size: 13px;
  }

  .plugin-mount-container {
    width: 100%;
    height: 100%;
  }
</style>
