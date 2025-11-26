import type { Plugin, PluginContext } from "../../sdk/types";
import StatusView from "./StatusView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "status",
    name: "Status",
    version: "0.1.0",
    description: "View financial data status",
    author: "Treeline",
  },

  activate(context: PluginContext) {
    // Register view
    context.registerView({
      id: "status",
      name: "Status",
      icon: "📊",
      component: StatusView,
    });

    // Add sidebar item
    context.registerSidebarItem({
      sectionId: "main",
      id: "status",
      label: "Status",
      icon: "📊",
      viewId: "status",
    });
  },
};
