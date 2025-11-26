/**
 * Plugin SDK Types
 *
 * Copy these from the main Treeline UI repo, or import them if developing
 * a plugin within the monorepo.
 */

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
}

export interface Plugin {
  manifest: PluginManifest;
  activate: (context: PluginContext) => void | Promise<void>;
  deactivate?: () => void | Promise<void>;
}

export interface PluginContext {
  registerView: (view: ViewRegistration) => void;
  registerSidebarSection: (section: SidebarSection) => void;
  registerSidebarItem: (item: SidebarItem) => void;
  registerCommand: (command: Command) => void;
  registerStatusBarItem: (item: StatusBarItem) => void;
  openView: (viewId: string) => void;
  executeCommand: (commandId: string) => void;
  db: any; // Database connection (not yet implemented)
  theme: ThemeManager;
}

export interface ViewRegistration {
  id: string;
  name: string;
  icon: string;
  /**
   * Mount function that renders the view into a target element
   * @param target - DOM element to render into
   * @param props - Props to pass to the component
   * @returns cleanup function to call when unmounting
   */
  mount: (target: HTMLElement, props: Record<string, any>) => () => void;
}

export interface SidebarSection {
  id: string;
  title: string;
  order: number;
}

export interface SidebarItem {
  sectionId: string;
  id: string;
  label: string;
  icon: string;
  viewId?: string;
  action?: () => void;
}

export interface Command {
  id: string;
  name: string;
  description?: string;
  execute: () => void | Promise<void>;
}

export interface StatusBarItem {
  id: string;
  text: string;
  tooltip?: string;
  alignment?: "left" | "right";
  priority?: number;
}

export interface ThemeManager {
  getCurrentTheme: () => "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
}
