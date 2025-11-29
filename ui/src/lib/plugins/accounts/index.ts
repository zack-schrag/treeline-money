import type { Plugin, PluginContext } from "../../sdk/types";
import AccountsView from "./AccountsView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "accounts",
    name: "Accounts",
    version: "0.1.0",
    description: "View and manage financial accounts",
    author: "Treeline",
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
