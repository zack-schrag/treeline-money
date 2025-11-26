/**
 * Plugin Registry - Central state for all plugin registrations
 *
 * This is a Svelte 5 runes-based store that holds all registered
 * sidebar items, views, commands, etc.
 */

import type {
  Plugin,
  PluginContext,
  SidebarSection,
  SidebarItem,
  ViewDefinition,
  Command,
  StatusBarItem,
  Tab,
  DatabaseInterface,
  ThemeInterface,
} from "./types";

// ============================================================================
// State (using Svelte 5 runes via module-level $state)
// ============================================================================

// Since we can't use runes at module level in .ts files,
// we'll use a class with methods that components can call

class PluginRegistry {
  // All registered plugins
  private plugins: Map<string, Plugin> = new Map();

  // Sidebar
  private _sidebarSections: SidebarSection[] = [];
  private _sidebarItems: SidebarItem[] = [];

  // Views
  private _views: Map<string, ViewDefinition> = new Map();

  // Commands
  private _commands: Map<string, Command> = new Map();

  // Status bar
  private _statusBarItems: StatusBarItem[] = [];

  // Tabs
  private _tabs: Tab[] = [];
  private _activeTabId: string | null = null;

  // Subscribers for reactivity
  private subscribers: Set<() => void> = new Set();

  // ============================================================================
  // Subscription for reactivity
  // ============================================================================

  subscribe(callback: () => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  private notify() {
    this.subscribers.forEach((cb) => cb());
  }

  // ============================================================================
  // Getters
  // ============================================================================

  get sidebarSections(): SidebarSection[] {
    return [...this._sidebarSections].sort((a, b) => a.order - b.order);
  }

  get sidebarItems(): SidebarItem[] {
    return [...this._sidebarItems].sort(
      (a, b) => (a.order ?? 0) - (b.order ?? 0)
    );
  }

  getSidebarItemsForSection(sectionId: string): SidebarItem[] {
    return this.sidebarItems.filter((item) => item.sectionId === sectionId);
  }

  get views(): ViewDefinition[] {
    return Array.from(this._views.values());
  }

  getView(viewId: string): ViewDefinition | undefined {
    return this._views.get(viewId);
  }

  get commands(): Command[] {
    return Array.from(this._commands.values());
  }

  get statusBarItems(): StatusBarItem[] {
    return [...this._statusBarItems].sort((a, b) => a.order - b.order);
  }

  get tabs(): Tab[] {
    return this._tabs;
  }

  get activeTabId(): string | null {
    return this._activeTabId;
  }

  get activeTab(): Tab | null {
    return this._tabs.find((t) => t.id === this._activeTabId) ?? null;
  }

  // ============================================================================
  // Registration methods (called by plugins)
  // ============================================================================

  registerSidebarSection(section: SidebarSection) {
    this._sidebarSections.push(section);
    this.notify();
  }

  registerSidebarItem(item: SidebarItem) {
    this._sidebarItems.push(item);
    this.notify();
  }

  registerView(view: ViewDefinition) {
    this._views.set(view.id, view);
    this.notify();
  }

  registerCommand(command: Command) {
    this._commands.set(command.id, command);
    this.notify();
  }

  registerStatusBarItem(item: StatusBarItem) {
    this._statusBarItems.push(item);
    this.notify();
  }

  // ============================================================================
  // Tab management
  // ============================================================================

  openView(viewId: string, props: Record<string, any> = {}) {
    const view = this._views.get(viewId);
    if (!view) {
      console.warn(`View not found: ${viewId}`);
      return;
    }

    // Check if view is already open and doesn't allow multiple
    if (!view.allowMultiple) {
      const existing = this._tabs.find((t) => t.viewId === viewId);
      if (existing) {
        this._activeTabId = existing.id;
        this.notify();
        return;
      }
    }

    // Create new tab
    const tab: Tab = {
      id: `tab-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      viewId,
      title: view.name,
      icon: view.icon,
      props: { ...view.defaultProps, ...props },
    };

    this._tabs.push(tab);
    this._activeTabId = tab.id;
    this.notify();
  }

  closeTab(tabId: string) {
    const index = this._tabs.findIndex((t) => t.id === tabId);
    if (index === -1) return;

    this._tabs.splice(index, 1);

    // If we closed the active tab, activate another
    if (this._activeTabId === tabId) {
      if (this._tabs.length > 0) {
        // Activate the tab to the left, or the first tab
        this._activeTabId = this._tabs[Math.max(0, index - 1)]?.id ?? null;
      } else {
        this._activeTabId = null;
      }
    }

    this.notify();
  }

  setActiveTab(tabId: string) {
    if (this._tabs.find((t) => t.id === tabId)) {
      this._activeTabId = tabId;
      this.notify();
    }
  }

  // ============================================================================
  // Command execution
  // ============================================================================

  executeCommand(commandId: string) {
    const command = this._commands.get(commandId);
    if (command) {
      command.execute();
    } else {
      console.warn(`Command not found: ${commandId}`);
    }
  }

  // ============================================================================
  // Plugin loading
  // ============================================================================

  async loadPlugin(plugin: Plugin, db: DatabaseInterface, theme: ThemeInterface) {
    if (this.plugins.has(plugin.manifest.id)) {
      console.warn(`Plugin already loaded: ${plugin.manifest.id}`);
      return;
    }

    // Create context for this plugin
    const ctx: PluginContext = {
      registerSidebarSection: (s) => this.registerSidebarSection(s),
      registerSidebarItem: (i) => this.registerSidebarItem(i),
      registerView: (v) => this.registerView(v),
      registerCommand: (c) => this.registerCommand(c),
      registerStatusBarItem: (i) => this.registerStatusBarItem(i),
      openView: (id, props) => this.openView(id, props),
      executeCommand: (id) => this.executeCommand(id),
      db,
      theme,
    };

    // Activate the plugin
    await plugin.activate(ctx);
    this.plugins.set(plugin.manifest.id, plugin);

    console.log(`Loaded plugin: ${plugin.manifest.name}`);
  }
}

// Singleton instance
export const registry = new PluginRegistry();
