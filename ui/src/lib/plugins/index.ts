/**
 * Plugin Registration
 *
 * Core plugins are registered here statically.
 * External plugins are loaded dynamically from ~/.treeline/plugins/
 */

import { invoke } from "@tauri-apps/api/core";
import { convertFileSrc } from "@tauri-apps/api/core";
import { registry, themeManager } from "../sdk";
import type { Plugin, PluginContext } from "../sdk";

// Import core plugins
import { plugin as statusPlugin } from "./status";
import { plugin as queryPlugin } from "./query";

// List of core plugins (built into the app)
const corePlugins: Plugin[] = [statusPlugin, queryPlugin];

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

  // Combine core and external plugins
  const allPlugins = [...corePlugins, ...externalPlugins];

  console.log(`Initializing ${allPlugins.length} plugin(s) (${corePlugins.length} core, ${externalPlugins.length} external)...`);

  // Register core sidebar section
  registry.registerSidebarSection({
    id: "main",
    title: "Main",
    order: 1,
  });

  for (const plugin of allPlugins) {
    try {
      // Create context with plugin API
      const context: PluginContext = {
        registerSidebarSection: registry.registerSidebarSection.bind(registry),
        registerSidebarItem: registry.registerSidebarItem.bind(registry),
        registerView: registry.registerView.bind(registry),
        registerCommand: registry.registerCommand.bind(registry),
        registerStatusBarItem: registry.registerStatusBarItem.bind(registry),
        openView: registry.openView.bind(registry),
        executeCommand: registry.executeCommand.bind(registry),
        db: {} as any, // No database for now
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
