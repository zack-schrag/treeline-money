import type { Plugin, PluginContext } from "../../sdk/types";
import SettingsView from "./SettingsView.svelte";
import { runSync, toast, getDemoMode, setDemoMode } from "../../sdk";

export const plugin: Plugin = {
  manifest: {
    id: "settings",
    name: "Settings",
    version: "0.1.0",
    description: "App and plugin settings",
    author: "Treeline",
  },

  activate(context: PluginContext) {
    // Register view
    context.registerView({
      id: "settings",
      name: "Settings",
      icon: "⚙",
      component: SettingsView,
    });

    // Add sidebar item in footer section
    context.registerSidebarItem({
      sectionId: "system",
      id: "settings",
      label: "Settings",
      icon: "⚙",
      viewId: "settings",
    });

    // Register commands
    context.registerCommand({
      id: "settings:open",
      name: "Open Settings",
      category: "Settings",
      execute: () => {
        context.openView("settings");
      },
    });

    context.registerCommand({
      id: "data:sync",
      name: "Sync All Integrations",
      category: "Data",
      execute: async () => {
        toast.info("Syncing...", "Fetching data from integrations");
        try {
          const result = await runSync();
          const totalAccounts = result.results.reduce(
            (sum, r) => sum + (r.accounts_synced || 0),
            0
          );
          const totalTransactions = result.results.reduce(
            (sum, r) => sum + (r.transaction_stats?.new || r.transactions_synced || 0),
            0
          );

          // Check for errors
          const errors = result.results.filter((r) => r.error);
          if (errors.length > 0) {
            toast.warning(
              "Sync completed with warnings",
              errors.map((e) => e.error).join(", ")
            );
          } else {
            toast.success(
              "Sync complete",
              `${totalAccounts} accounts, ${totalTransactions} new transactions`
            );
          }
        } catch (e) {
          toast.error("Sync failed", e instanceof Error ? e.message : String(e));
        }
      },
    });

    context.registerCommand({
      id: "data:toggleDemoMode",
      name: "Toggle Demo Mode",
      category: "Data",
      execute: async () => {
        const current = await getDemoMode();
        const newMode = !current;
        await setDemoMode(newMode);

        if (newMode) {
          toast.info("Demo mode enabled", "Reload the app to use demo data");
        } else {
          toast.info("Demo mode disabled", "Reload the app to use real data");
        }
      },
    });
  },
};
