import type { Plugin, PluginContext } from "../../sdk/types";
import QueryView from "./QueryView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "query",
    name: "Query Runner",
    version: "0.1.0",
    description: "Execute SQL queries against your financial data",
    author: "Treeline",
  },

  activate(context: PluginContext) {
    // Register view
    context.registerView({
      id: "query",
      name: "Query",
      icon: "⚡",
      component: QueryView,
    });

    // Add sidebar item
    context.registerSidebarItem({
      sectionId: "main",
      id: "query",
      label: "Query",
      icon: "⚡",
      viewId: "query",
    });
  },
};
