<script lang="ts">
  import { registry } from "../sdk";

  // Reactive state
  let sections = $state(registry.sidebarSections);
  let items = $state(registry.sidebarItems);

  // Subscribe to registry changes
  $effect(() => {
    return registry.subscribe(() => {
      sections = registry.sidebarSections;
      items = registry.sidebarItems;
    });
  });

  function getItemsForSection(sectionId: string) {
    return items.filter((item) => item.sectionId === sectionId);
  }

  function handleItemClick(viewId: string) {
    registry.openView(viewId);
  }

  // Track active view for highlighting
  let activeViewId = $derived(registry.activeTab?.viewId ?? null);
</script>

<aside class="sidebar">
  <div class="sidebar-header">
    <span class="logo">◈</span>
    <span class="title">treeline</span>
  </div>

  <nav class="sidebar-nav">
    {#each sections as section}
      <div class="sidebar-section">
        <div class="section-title">{section.title}</div>
        <ul class="section-items">
          {#each getItemsForSection(section.id) as item}
            <li>
              <button
                class="sidebar-item"
                class:active={activeViewId === item.viewId}
                onclick={() => handleItemClick(item.viewId)}
              >
                <span class="item-icon">{item.icon}</span>
                <span class="item-label">{item.label}</span>
                {#if item.shortcut}
                  <span class="item-shortcut">{item.shortcut}</span>
                {/if}
              </button>
            </li>
          {/each}
        </ul>
      </div>
    {/each}
  </nav>

  <div class="sidebar-footer">
    <button class="sidebar-item" onclick={() => registry.executeCommand("core:command-palette")}>
      <span class="item-icon">⌘</span>
      <span class="item-label">Commands</span>
      <span class="item-shortcut">⌘K</span>
    </button>
  </div>
</aside>

<style>
  .sidebar {
    width: 220px;
    height: 100%;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--sidebar-border);
    display: flex;
    flex-direction: column;
    user-select: none;
  }

  .sidebar-header {
    padding: var(--spacing-md) var(--spacing-lg);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    border-bottom: 1px solid var(--sidebar-border);
  }

  .logo {
    font-size: 18px;
    color: var(--accent-primary);
  }

  .title {
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.5px;
  }

  .sidebar-nav {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-sm) 0;
  }

  .sidebar-section {
    margin-bottom: var(--spacing-md);
  }

  .section-title {
    padding: var(--spacing-xs) var(--spacing-lg);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .section-items {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .sidebar-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-lg);
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 13px;
    font-family: var(--font-sans);
    cursor: pointer;
    text-align: left;
    transition: background 0.1s, color 0.1s;
  }

  .sidebar-item:hover {
    background: var(--sidebar-item-hover);
    color: var(--text-primary);
  }

  .sidebar-item.active {
    background: var(--sidebar-item-active);
    color: var(--text-primary);
    border-left: 2px solid var(--accent-primary);
    padding-left: calc(var(--spacing-lg) - 2px);
  }

  .item-icon {
    width: 18px;
    text-align: center;
    flex-shrink: 0;
  }

  .item-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .item-shortcut {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .sidebar-footer {
    border-top: 1px solid var(--sidebar-border);
    padding: var(--spacing-sm) 0;
  }
</style>
