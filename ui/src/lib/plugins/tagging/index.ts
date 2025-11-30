import type { Plugin, PluginContext } from "../../sdk/types";
import TaggingView from "./TaggingView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "transactions",
    name: "Transactions",
    version: "0.1.0",
    description: "Browse, tag, edit, and split transactions",
    author: "Treeline",
  },

  activate(context: PluginContext) {
    // Register view
    context.registerView({
      id: "transactions",
      name: "Transactions",
      icon: "💳",
      component: TaggingView,
    });

    // Add sidebar item
    context.registerSidebarItem({
      sectionId: "main",
      id: "transactions",
      label: "Transactions",
      icon: "💳",
      viewId: "transactions",
    });
  },
};
