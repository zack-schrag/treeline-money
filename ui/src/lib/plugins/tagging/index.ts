import type { Plugin, PluginContext } from "../../sdk/types";
import TaggingView from "./TaggingView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "tagging",
    name: "Tagging",
    version: "0.1.0",
    description: "Tag transactions with keyboard-driven interface",
    author: "Treeline",
  },

  activate(context: PluginContext) {
    // Register view
    context.registerView({
      id: "tagging",
      name: "Tagging",
      icon: "🏷️",
      component: TaggingView,
    });

    // Add sidebar item
    context.registerSidebarItem({
      sectionId: "main",
      id: "tagging",
      label: "Tagging",
      icon: "🏷️",
      viewId: "tagging",
    });
  },
};
