import type { Plugin, PluginContext } from "../../sdk/types";
import { runSync, toast, getDemoMode, enableDemo, disableDemo, registry } from "../../sdk";

export const plugin: Plugin = {
  manifest: {
    id: "settings",
    name: "Settings",
    version: "0.1.0",
    description: "App and plugin settings",
    author: "Treeline",
  },

  activate(context: PluginContext) {
    // Settings view is now a modal opened via core:settings command
    // This plugin just registers utility commands

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

        try {
          if (newMode) {
            toast.info("Enabling demo mode...", "Setting up demo data");
            await enableDemo();
            toast.success("Demo mode enabled", "Switched to demo data");
          } else {
            toast.info("Disabling demo mode...", "Switching to real data");
            await disableDemo();
            toast.success("Demo mode disabled", "Switched to real data");
          }

          // Emit refresh event so all open views reload their data
          registry.emit("data:refresh");
        } catch (e) {
          toast.error("Demo mode toggle failed", e instanceof Error ? e.message : String(e));
        }
      },
    });
  },
};
