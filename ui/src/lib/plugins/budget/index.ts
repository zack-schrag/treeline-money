import type { Plugin, PluginContext } from "../../sdk/types";
import BudgetView from "./BudgetView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "budget",
    name: "Budget",
    version: "0.1.0",
    description: "Track spending against tag-based budget categories",
    author: "Treeline",
    permissions: {
      tables: {
        read: ["transactions", "sys_plugin_budget_categories", "sys_plugin_budget_rollovers"],
        create: ["sys_plugin_budget_categories", "sys_plugin_budget_rollovers"],
      },
    },
  },

  activate(context: PluginContext) {
    // Register view
    context.registerView({
      id: "budget",
      name: "Budget",
      icon: "💰",
      component: BudgetView,
    });

    // Add sidebar item
    context.registerSidebarItem({
      sectionId: "main",
      id: "budget",
      label: "Budget",
      icon: "💰",
      viewId: "budget",
    });
  },
};
