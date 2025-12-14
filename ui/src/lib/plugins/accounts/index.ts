import type { Plugin, PluginContext } from "../../sdk/types";
import AccountsView from "./AccountsView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "accounts",
    name: "Accounts",
    version: "0.1.0",
    description: "View and manage financial accounts",
    author: "Treeline",
    permissions: {
      tables: {
        write: ["sys_accounts", "sys_balance_snapshots", "sys_plugin_accounts_overrides"],
      },
    },
  },

  activate(context: PluginContext) {
    // Register view
    context.registerView({
      id: "accounts",
      name: "Accounts",
      icon: "🏦",
      component: AccountsView,
    });

    // Add sidebar item
    context.registerSidebarItem({
      sectionId: "main",
      id: "accounts",
      label: "Accounts",
      icon: "🏦",
      viewId: "accounts",
    });

  },
};
