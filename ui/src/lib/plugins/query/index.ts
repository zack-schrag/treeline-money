import type { Plugin, PluginContext } from "../../sdk/types";
import QueryView from "./QueryView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "query",
    name: "Query Runner",
    version: "0.1.0",
    description: "Execute SQL queries against your financial data",
    author: "Treeline",
    permissions: {
      tables: {
        read: ["*"],  // Query editor can read any table
        create: ["sys_plugin_query_history"],
      },
    },
  },

  activate(context: PluginContext) {
    // Register view - allowMultiple enables opening multiple query tabs
    context.registerView({
      id: "query",
      name: "Query",
      icon: "⚡",
      component: QueryView,
      allowMultiple: true,
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
