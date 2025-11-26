import type { Plugin, PluginContext } from "./types";
import HelloWorldView from "./HelloWorldView.svelte";
import { mount, unmount } from "svelte";

export const plugin: Plugin = {
  manifest: {
    id: "hello-world",
    name: "Hello World",
    version: "0.1.0",
    description: "An example plugin demonstrating the Treeline plugin system",
    author: "Your Name",
  },

  activate(context: PluginContext) {
    console.log("Hello World plugin activated!");

    // Register the view with a mount function
    context.registerView({
      id: "hello-world-view",
      name: "Hello World",
      icon: "👋",
      mount: (target: HTMLElement, props: Record<string, any>) => {
        // Mount the Svelte component using our bundled Svelte runtime
        const instance = mount(HelloWorldView, {
          target,
          props,
        });

        // Return cleanup function
        return () => {
          unmount(instance);
        };
      },
    });

    // Add sidebar item
    context.registerSidebarItem({
      sectionId: "main",
      id: "hello-world",
      label: "Hello World",
      icon: "👋",
      viewId: "hello-world-view",
    });

    // Register a command (optional)
    context.registerCommand({
      id: "hello-world.greet",
      name: "Say Hello",
      description: "Display a greeting message",
      execute: () => {
        console.log("👋 Hello from the Hello World plugin!");
      },
    });

    console.log("✓ Hello World plugin registered");
  },

  deactivate() {
    console.log("Hello World plugin deactivated");
  },
};
