<script lang="ts">
  import { onMount } from "svelte";
  import { registry, getAppSetting, setAppSetting } from "../sdk";
  import { Icon } from "../shared";

  // Icon mapping for sidebar items
  const iconMap: Record<string, string> = {
    "🏦": "bank",
    "💰": "wallet",
    "💳": "credit-card",
    "🏷": "tag",
    "⚡": "zap",
    "⚙": "settings",
    "📊": "chart",
    "🔍": "search",
  };

  function getIconName(emoji: string): string {
    return iconMap[emoji] || "database";
  }

  // Collapsed state
  let isCollapsed = $state(false);

  onMount(async () => {
    // Load collapsed state from settings
    const collapsed = await getAppSetting("sidebarCollapsed");
    if (collapsed !== undefined) {
      isCollapsed = collapsed;
    }
  });

  async function toggleCollapsed() {
    isCollapsed = !isCollapsed;
    await setAppSetting("sidebarCollapsed", isCollapsed);
  }

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
    // Filter out settings - it's now in the footer as a modal
    return items.filter((item) => item.sectionId === sectionId && item.viewId !== "settings");
  }

  function handleItemClick(viewId: string) {
    registry.openView(viewId);
  }

  // Track active view for highlighting
  let activeViewId = $derived(registry.activeTab?.viewId ?? null);
</script>

<aside class="sidebar" class:collapsed={isCollapsed}>
  <div class="sidebar-header">
    {#if isCollapsed}
      <button class="expand-btn" onclick={toggleCollapsed} title="Expand sidebar">
        <span class="logo">◈</span>
      </button>
    {:else}
      <span class="logo">◈</span>
      <span class="title">treeline</span>
      <button class="collapse-btn" onclick={toggleCollapsed} title="Collapse sidebar">
        <Icon name="chevron-down" size={14} />
      </button>
    {/if}
  </div>

  <nav class="sidebar-nav">
    {#each sections as section}
      <div class="sidebar-section">
        {#if !isCollapsed}
          <div class="section-title">{section.title}</div>
        {/if}
        <ul class="section-items">
          {#each getItemsForSection(section.id) as item}
            <li>
              <button
                class="sidebar-item"
                class:active={activeViewId === item.viewId}
                onclick={() => handleItemClick(item.viewId)}
                title={isCollapsed ? item.label : undefined}
              >
                <span class="item-icon">
                  <Icon name={getIconName(item.icon)} size={16} />
                </span>
                {#if !isCollapsed}
                  <span class="item-label">{item.label}</span>
                  {#if item.shortcut}
                    <span class="item-shortcut">{item.shortcut}</span>
                  {/if}
                {/if}
              </button>
            </li>
          {/each}
        </ul>
      </div>
    {/each}
  </nav>

  <div class="sidebar-footer">
    <button class="sidebar-item" onclick={() => registry.executeCommand("core:settings")} title={isCollapsed ? "Settings" : undefined}>
      <span class="item-icon">
        <Icon name="settings" size={16} />
      </span>
      {#if !isCollapsed}
        <span class="item-label">Settings</span>
        <span class="item-shortcut">⌘,</span>
      {/if}
    </button>
    <button class="sidebar-item" onclick={() => registry.executeCommand("core:command-palette")} title={isCollapsed ? "Commands" : undefined}>
      <span class="item-icon">
        <Icon name="command" size={16} />
      </span>
      {#if !isCollapsed}
        <span class="item-label">Commands</span>
        <span class="item-shortcut">⌘P</span>
      {/if}
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
    transition: width 0.15s ease;
  }

  .sidebar.collapsed {
    width: 52px;
  }

  .sidebar-header {
    padding: var(--spacing-md) var(--spacing-lg);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    border-bottom: 1px solid var(--sidebar-border);
  }

  .sidebar.collapsed .sidebar-header {
    padding: var(--spacing-md) var(--spacing-sm);
    justify-content: center;
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
    flex: 1;
  }

  .collapse-btn {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.1s, background 0.1s;
  }

  .collapse-btn:hover {
    color: var(--text-primary);
    background: var(--sidebar-item-hover);
  }

  .expand-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.15s ease;
  }

  .expand-btn:hover {
    transform: scale(1.1);
  }

  .expand-btn .logo {
    font-size: 18px;
    color: var(--accent-primary);
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

  .sidebar.collapsed .sidebar-item {
    padding: var(--spacing-sm);
    justify-content: center;
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

  .sidebar.collapsed .sidebar-item.active {
    padding-left: calc(var(--spacing-sm) - 2px);
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
    font-size: 12px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .sidebar-footer {
    border-top: 1px solid var(--sidebar-border);
    padding: var(--spacing-sm) 0;
  }
</style>
