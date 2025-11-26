/**
 * Treeline Plugin SDK
 *
 * This is the main entry point for plugin authors.
 * Import from '@treeline/sdk' (aliased in the build config)
 */

// Types
export type {
  Plugin,
  PluginManifest,
  PluginContext,
  SidebarSection,
  SidebarItem,
  ViewDefinition,
  Command,
  StatusBarItem,
  Tab,
  ThemeInterface,
} from "./types";

// Registry (for core use)
export { registry } from "./registry";

// API
export { getStatus, executeQuery } from "./api";
export type { StatusResponse, QueryResult } from "./api";

// Theme
export { themeManager, themes } from "./theme";
export type { ThemeDefinition } from "./theme";
