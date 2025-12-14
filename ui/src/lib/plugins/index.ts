/**
 * Plugin Registration
 *
 * Core plugins are registered here statically.
 * External plugins are loaded dynamically from ~/.treeline/plugins/
 */

import { invoke } from "@tauri-apps/api/core";
import { convertFileSrc } from "@tauri-apps/api/core";
import { registry, themeManager, getDisabledPlugins } from "../sdk";
import type { Plugin, PluginContext } from "../sdk";

// Import core plugins
import { plugin as queryPlugin } from "./query";
import { plugin as taggingPlugin } from "./tagging";
import { plugin as budgetPlugin } from "./budget";
import { plugin as accountsPlugin } from "./accounts";

// List of core plugins (built into the app)
const corePlugins: Plugin[] = [accountsPlugin, budgetPlugin, taggingPlugin, queryPlugin];

interface ExternalPluginInfo {
  manifest: {
    id: string;
    name: string;
    version: string;
    description: string;
    author: string;
    main: string;
  };
  path: string;
}

/**
 * Load external plugins from ~/.treeline/plugins/
 */
async function loadExternalPlugins(): Promise<Plugin[]> {
  try {
    // Get the plugins directory path
    const pluginsDir = await invoke<string>("get_plugins_dir");

    // Discover all available plugins
    const discovered = await invoke<ExternalPluginInfo[]>("discover_plugins");
    const plugins: Plugin[] = [];

    for (const pluginInfo of discovered) {
      try {
        // Construct the full path to the plugin file
        const pluginPath = `${pluginsDir}/${pluginInfo.manifest.id}/${pluginInfo.manifest.main}`;

        // Convert to asset URL that Tauri can load
        const assetUrl = convertFileSrc(pluginPath);

        console.log(`Loading external plugin from: ${assetUrl}`);

        // Dynamically import the plugin module
        const module = await import(/* @vite-ignore */ assetUrl);

        if (module.plugin) {
          plugins.push(module.plugin);
          console.log(`✓ Discovered external plugin: ${pluginInfo.manifest.name}`);
        } else {
          console.error(`✗ External plugin ${pluginInfo.manifest.id} does not export 'plugin'`);
        }
      } catch (error) {
        console.error(`✗ Failed to load external plugin ${pluginInfo.manifest.id}:`, error);
      }
    }

    return plugins;
  } catch (error) {
    console.error("Failed to discover external plugins:", error);
    return [];
  }
}

/**
 * Initialize all plugins (core + external)
 */
export async function initializePlugins(): Promise<void> {
  // Load external plugins
  const externalPlugins = await loadExternalPlugins();

  // Get list of disabled plugins
  const disabledPlugins = await getDisabledPlugins();

  // Combine core and external plugins
  const allPlugins = [...corePlugins, ...externalPlugins];

  console.log(`Initializing ${allPlugins.length} plugin(s) (${corePlugins.length} core, ${externalPlugins.length} external)...`);
  if (disabledPlugins.length > 0) {
    console.log(`Disabled plugins: ${disabledPlugins.join(", ")}`);
  }

  // Register core sidebar sections
  registry.registerSidebarSection({
    id: "main",
    title: "Views",
    order: 1,
  });

  for (const plugin of allPlugins) {
    // Skip disabled plugins
    if (disabledPlugins.includes(plugin.manifest.id)) {
      console.log(`⊘ Skipped disabled plugin: ${plugin.manifest.name} (${plugin.manifest.id})`);
      continue;
    }

    try {
      const pluginId = plugin.manifest.id;

      // Register plugin permissions
      const writeTables = plugin.manifest.permissions?.tables?.write ?? [];
      registry.setPluginPermissions(pluginId, writeTables);

      // Create context with plugin API
      const context: PluginContext = {
        registerSidebarSection: registry.registerSidebarSection.bind(registry),
        registerSidebarItem: registry.registerSidebarItem.bind(registry),
        // Pass pluginId to registerView for permission tracking
        registerView: (view) => registry.registerView(view, pluginId),
        registerCommand: registry.registerCommand.bind(registry),
        registerStatusBarItem: registry.registerStatusBarItem.bind(registry),
        openView: registry.openView.bind(registry),
        executeCommand: registry.executeCommand.bind(registry),
        db: {} as any, // Database access is provided via SDK props
        theme: themeManager,
      };

      // Activate plugin
      await plugin.activate(context);

      console.log(`✓ Loaded plugin: ${plugin.manifest.name} (${plugin.manifest.id})`);
    } catch (error) {
      console.error(`✗ Failed to load plugin: ${plugin.manifest.name}`, error);
    }
  }
}

/**
 * Get list of all available core plugins (for settings UI)
 */
export function getCorePluginManifests() {
  return corePlugins.map(p => p.manifest);
}
