/**
 * Settings Service
 *
 * Provides a unified interface for app and plugin settings.
 *
 * Pattern for plugin developers:
 * - Settings (this file): User preferences, editable via Settings UI
 * - State (pluginState): Plugin runtime data, not user-editable
 * - Plugin files (read/write_plugin_config): Domain data like budget months
 */

import { invoke } from "@tauri-apps/api/core";

/**
 * App-level settings structure
 */
export interface AppSettings {
  theme: "light" | "dark" | "system";
  lastSyncDate: string | null;
  autoSyncOnStartup: boolean;
}

/**
 * Full settings structure
 */
export interface Settings {
  app: AppSettings;
  plugins: Record<string, Record<string, unknown>>;
  disabledPlugins?: string[];
}

/**
 * Default settings
 */
const DEFAULT_SETTINGS: Settings = {
  app: {
    theme: "dark",
    lastSyncDate: null,
    autoSyncOnStartup: true,
  },
  plugins: {},
};

// In-memory cache of settings
let settingsCache: Settings | null = null;

// Subscribers for settings changes
type SettingsSubscriber = (settings: Settings) => void;
const subscribers: Set<SettingsSubscriber> = new Set();

/**
 * Read all settings from disk
 */
export async function readSettings(): Promise<Settings> {
  const jsonString = await invoke<string>("read_settings");
  const parsed = JSON.parse(jsonString);

  // Merge with defaults to ensure all fields exist
  settingsCache = {
    app: { ...DEFAULT_SETTINGS.app, ...parsed.app },
    plugins: { ...DEFAULT_SETTINGS.plugins, ...parsed.plugins },
    disabledPlugins: parsed.disabledPlugins || [],
  };

  return settingsCache;
}

/**
 * Write all settings to disk
 */
export async function writeSettings(settings: Settings): Promise<void> {
  await invoke("write_settings", { content: JSON.stringify(settings, null, 2) });
  settingsCache = settings;
  notifySubscribers();
}

/**
 * Get current settings (from cache or disk)
 */
export async function getSettings(): Promise<Settings> {
  if (settingsCache) {
    return settingsCache;
  }
  return readSettings();
}

/**
 * Get a specific app setting
 */
export async function getAppSetting<K extends keyof AppSettings>(key: K): Promise<AppSettings[K]> {
  const settings = await getSettings();
  return settings.app[key];
}

/**
 * Set a specific app setting
 */
export async function setAppSetting<K extends keyof AppSettings>(
  key: K,
  value: AppSettings[K]
): Promise<void> {
  const settings = await getSettings();
  settings.app[key] = value;
  await writeSettings(settings);
}

/**
 * Get all settings for a plugin
 */
export async function getPluginSettings<T extends Record<string, unknown>>(
  pluginId: string,
  defaults: T
): Promise<T> {
  const settings = await getSettings();
  const pluginSettings = settings.plugins[pluginId] || {};
  return { ...defaults, ...pluginSettings } as T;
}

/**
 * Set all settings for a plugin
 */
export async function setPluginSettings(
  pluginId: string,
  pluginSettings: Record<string, unknown>
): Promise<void> {
  const settings = await getSettings();
  settings.plugins[pluginId] = pluginSettings;
  await writeSettings(settings);
}

/**
 * Update specific plugin settings (merge with existing)
 */
export async function updatePluginSettings(
  pluginId: string,
  updates: Record<string, unknown>
): Promise<void> {
  const settings = await getSettings();
  settings.plugins[pluginId] = {
    ...(settings.plugins[pluginId] || {}),
    ...updates,
  };
  await writeSettings(settings);
}

/**
 * Subscribe to settings changes
 */
export function subscribeToSettings(callback: SettingsSubscriber): () => void {
  subscribers.add(callback);
  return () => subscribers.delete(callback);
}

/**
 * Notify all subscribers of settings changes
 */
function notifySubscribers(): void {
  if (settingsCache) {
    subscribers.forEach((callback) => callback(settingsCache!));
  }
}

/**
 * Clear settings cache (useful for testing or forced refresh)
 */
export function clearSettingsCache(): void {
  settingsCache = null;
}

// ============================================================================
// Plugin State (separate from settings - runtime state, not user preferences)
// ============================================================================

/**
 * Read plugin state (runtime state, not user settings)
 */
export async function readPluginState<T>(pluginId: string): Promise<T | null> {
  const jsonString = await invoke<string>("read_plugin_state", { pluginId });
  if (jsonString === "null") {
    return null;
  }
  return JSON.parse(jsonString) as T;
}

/**
 * Write plugin state (runtime state, not user settings)
 */
export async function writePluginState<T>(pluginId: string, state: T): Promise<void> {
  await invoke("write_plugin_state", {
    pluginId,
    content: JSON.stringify(state, null, 2)
  });
}

// ============================================================================
// Sync
// ============================================================================

export interface SyncResult {
  results: Array<{
    integration: string;
    accounts_synced: number;
    transactions_synced: number;
    transaction_stats?: {
      discovered: number;
      new: number;
      skipped: number;
    };
    error?: string;
  }>;
}

/**
 * Run sync and update lastSyncDate
 */
export async function runSync(): Promise<SyncResult> {
  const jsonString = await invoke<string>("run_sync");
  const result = JSON.parse(jsonString) as SyncResult;

  // Update lastSyncDate on success
  const today = new Date().toISOString().split("T")[0];
  await setAppSetting("lastSyncDate", today);

  return result;
}

/**
 * Check if sync is needed (based on lastSyncDate)
 */
export async function isSyncNeeded(): Promise<boolean> {
  const settings = await getSettings();

  if (!settings.app.autoSyncOnStartup) {
    return false;
  }

  const lastSyncDate = settings.app.lastSyncDate;
  if (!lastSyncDate) {
    return true;
  }

  const today = new Date().toISOString().split("T")[0];
  return lastSyncDate < today;
}

// ============================================================================
// Demo Mode
// ============================================================================

/**
 * Get current demo mode status
 */
export async function getDemoMode(): Promise<boolean> {
  return invoke<boolean>("get_demo_mode");
}

/**
 * Set demo mode (requires window reload to take effect)
 */
export async function setDemoMode(enabled: boolean): Promise<void> {
  await invoke("set_demo_mode", { enabled });
}
