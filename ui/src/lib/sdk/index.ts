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
export type { StatusResponse, QueryResult, ExecuteQueryOptions } from "./api";

// Theme
export { themeManager, themes } from "./theme";
export type { ThemeDefinition } from "./theme";

// Settings
export {
  readSettings,
  writeSettings,
  getSettings,
  getAppSetting,
  setAppSetting,
  getPluginSettings,
  setPluginSettings,
  updatePluginSettings,
  subscribeToSettings,
  clearSettingsCache,
  readPluginState,
  writePluginState,
  runSync,
  isSyncNeeded,
  getDemoMode,
  setDemoMode,
  // CSV Import
  pickCsvFile,
  getCsvHeaders,
  importCsvPreview,
  importCsvExecute,
  // Integrations
  setupSimplefin,
} from "./settings";
export type {
  Settings,
  AppSettings,
  SyncResult,
  ImportColumnMapping,
  ImportPreviewResult,
  ImportExecuteResult,
} from "./settings";

// Toast notifications
export { toast, showToast, dismissToast, dismissAllToasts } from "./toast.svelte";
export type { Toast, ToastOptions, ToastType } from "./toast.svelte";
