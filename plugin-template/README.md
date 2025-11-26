# Treeline Plugin Template

This is a template for creating external plugins for Treeline. Plugins extend Treeline's functionality by adding new views, commands, and UI elements.

## Quick Start

### 1. Copy this template

```bash
cp -r plugin-template my-plugin
cd my-plugin
```

### 2. Install dependencies

```bash
npm install
```

### 3. Customize your plugin

Edit `manifest.json`:
```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "0.1.0",
  "description": "Description of what my plugin does",
  "author": "Your Name",
  "main": "index.js"
}
```

### 4. Develop your plugin

Edit `src/index.ts` and `src/HelloWorldView.svelte` to implement your plugin's functionality.

### 5. Build the plugin

```bash
npm run build
```

This creates `dist/index.js` - the compiled plugin ready to be installed.

### 6. Install the plugin

Copy the plugin to Treeline's plugins directory:

```bash
mkdir -p ~/.treeline/plugins/my-plugin
cp manifest.json ~/.treeline/plugins/my-plugin/
cp dist/index.js ~/.treeline/plugins/my-plugin/
```

### 7. Restart Treeline

The plugin will be loaded automatically when Treeline starts.

## Development Workflow

### Watch mode

For faster development, use watch mode:

```bash
npm run dev
```

This automatically rebuilds when you make changes. You'll still need to restart Treeline to see the changes.

### Plugin structure

```
my-plugin/
├── manifest.json          # Plugin metadata
├── src/
│   ├── index.ts          # Plugin entry point
│   ├── types.ts          # TypeScript type definitions
│   └── MyView.svelte     # Svelte components
├── dist/
│   └── index.js          # Built plugin (generated)
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## Plugin API

### Plugin manifest

Every plugin must export a `plugin` object with this structure:

```typescript
export const plugin: Plugin = {
  manifest: {
    id: "unique-plugin-id",
    name: "Display Name",
    version: "0.1.0",
    description: "What this plugin does",
    author: "Your Name",
  },

  activate(context: PluginContext) {
    // Register views, commands, etc.
  },

  deactivate() {
    // Optional cleanup
  },
};
```

### PluginContext API

The `context` object passed to `activate()` provides these methods:

#### Register a view

```typescript
context.registerView({
  id: "my-view",
  name: "My View",
  icon: "🔧",
  component: MyViewComponent,
});
```

#### Register a sidebar item

```typescript
context.registerSidebarItem({
  sectionId: "main",
  id: "my-sidebar-item",
  label: "My Plugin",
  icon: "🔧",
  viewId: "my-view",
});
```

#### Register a command

```typescript
context.registerCommand({
  id: "my-plugin.do-something",
  name: "Do Something",
  description: "Description of what this command does",
  handler: async () => {
    // Command implementation
  },
});
```

#### Register a sidebar section

```typescript
context.registerSidebarSection({
  id: "my-section",
  title: "My Section",
  order: 10,
});
```

#### Register a status bar item

```typescript
context.registerStatusBarItem({
  id: "my-status",
  text: "Status",
  tooltip: "Hover text",
  alignment: "right",
  priority: 10,
});
```

## Svelte Components

Plugins can use Svelte 5 components with runes:

```svelte
<script lang="ts">
  let count = $state(0);

  function increment() {
    count++;
  }
</script>

<div class="p-6">
  <h1>Count: {count}</h1>
  <button onclick={increment}>Increment</button>
</div>
```

### Styling

Use Tailwind CSS classes for styling. The main app includes Tailwind, so all utility classes are available.

## Calling the Treeline CLI

Plugins can call the Treeline CLI using Tauri's invoke API:

```typescript
import { invoke } from "@tauri-apps/api/core";

// Call a Tauri command
const result = await invoke("status");
```

For custom CLI commands, you'll need to add them to the Tauri backend.

## Examples

### Simple counter plugin

```typescript
import type { Plugin, PluginContext } from "./types";
import CounterView from "./CounterView.svelte";

export const plugin: Plugin = {
  manifest: {
    id: "counter",
    name: "Counter",
    version: "1.0.0",
    description: "A simple counter",
    author: "Me",
  },

  activate(context: PluginContext) {
    context.registerView({
      id: "counter-view",
      name: "Counter",
      icon: "🔢",
      component: CounterView,
    });

    context.registerSidebarItem({
      sectionId: "main",
      id: "counter",
      label: "Counter",
      icon: "🔢",
      viewId: "counter-view",
    });
  },
};
```

## Tips

- **Keep plugins lightweight** - Users should be able to load multiple plugins without performance issues
- **Handle errors gracefully** - Don't crash the app if something goes wrong
- **Use TypeScript** - Get better IDE support and catch errors early
- **Follow Tailwind conventions** - Use the same styling as the main app for consistency
- **Test thoroughly** - Make sure your plugin works before publishing

## Troubleshooting

### Plugin not loading

1. Check the browser console for errors (open DevTools)
2. Verify `manifest.json` is valid JSON
3. Ensure `dist/index.js` exists after building
4. Check that the plugin is in `~/.treeline/plugins/your-plugin-id/`

### Build errors

1. Run `npm install` to ensure dependencies are installed
2. Check that TypeScript types are correct
3. Make sure Svelte components have valid syntax

### Component not rendering

1. Ensure the component is imported in `src/index.ts`
2. Check that you're registering both the view and sidebar item
3. Verify the sidebar section exists ("main" is created by default)

## Distribution

Once your plugin is ready, you can distribute it by:

1. **GitHub repository** - Users can clone and build
2. **Pre-built releases** - Attach `manifest.json` and `dist/index.js` to GitHub releases
3. **Plugin marketplace** - Coming soon!

## Next Steps

- Browse the [Treeline SDK documentation](../ui/src/lib/sdk/) for more API details
- Check out example plugins in the community
- Share your plugin with other users!
