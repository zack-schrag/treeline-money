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

Edit `src/index.ts` and create your Svelte views to implement your plugin's functionality.

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

## Plugin SDK

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
    // Declare tables your plugin needs write access to
    permissions: {
      tables: {
        write: ["sys_plugin_my_plugin_data"],
      },
    },
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

```typescript
// Register a view with a mount function
context.registerView({
  id: "my-view",
  name: "My View",
  icon: "🔧",
  mount: (target, props) => {
    // props.sdk contains the Plugin SDK
    const instance = mount(MyComponent, { target, props });
    return () => unmount(instance);
  },
});

// Add to sidebar
context.registerSidebarItem({
  sectionId: "main",
  id: "my-sidebar-item",
  label: "My Plugin",
  icon: "🔧",
  viewId: "my-view",
});

// Register a command (appears in Cmd+P palette)
context.registerCommand({
  id: "my-plugin.do-something",
  name: "Do Something",
  execute: async () => {
    // Command implementation
  },
});
```

### Plugin SDK (in views)

Your view components receive the SDK via `props.sdk`. This is the main API for interacting with Treeline:

```svelte
<script lang="ts">
  import type { PluginSDK } from "./types";

  interface Props {
    sdk: PluginSDK;
  }
  let { sdk }: Props = $props();

  // Query the database
  const accounts = await sdk.query("SELECT * FROM sys_accounts");

  // Write to your plugin's tables
  await sdk.execute("INSERT INTO sys_plugin_my_plugin_data VALUES (...)");

  // Show notifications
  sdk.toast.success("Done!", "Operation completed");
  sdk.toast.error("Oops", "Something went wrong");

  // Navigate to another view
  sdk.openView("transactions");

  // React to data changes (after sync/import)
  sdk.onDataRefresh(() => {
    // Reload your data
  });

  // Persist settings
  await sdk.settings.set({ myOption: true });
  const settings = await sdk.settings.get();

  // Get current theme
  const theme = sdk.theme.current(); // "light" or "dark"
</script>
```

### Available SDK Methods

| Method | Description |
|--------|-------------|
| `sdk.query(sql)` | Execute a read-only SQL query |
| `sdk.execute(sql)` | Write to your plugin's tables |
| `sdk.toast.success/error/info/warning(message, description?)` | Show notifications |
| `sdk.openView(viewId, props?)` | Navigate to a view |
| `sdk.onDataRefresh(callback)` | Subscribe to data refresh events |
| `sdk.emitDataRefresh()` | Notify other views that data changed |
| `sdk.theme.current()` | Get current theme ("light" or "dark") |
| `sdk.theme.subscribe(callback)` | React to theme changes |
| `sdk.settings.get()` | Load persisted plugin settings |
| `sdk.settings.set(data)` | Save plugin settings |
| `sdk.state.read()` | Load ephemeral plugin state |
| `sdk.state.write(data)` | Save ephemeral plugin state |
| `sdk.modKey` | "Cmd" on Mac, "Ctrl" on Windows/Linux |
| `sdk.formatShortcut(shortcut)` | Format shortcut for display |

### Database Access

Plugins can read any table using `sdk.query()`:

```typescript
// Read transactions
const txns = await sdk.query(`
  SELECT * FROM transactions
  WHERE tags @> ['groceries']
  ORDER BY transaction_date DESC
  LIMIT 100
`);

// Read accounts
const accounts = await sdk.query(`
  SELECT * FROM sys_accounts
  WHERE is_deleted = false
`);
```

To write data, plugins must declare their tables in `permissions.tables.write`. Community plugins can only write to `sys_plugin_{plugin_id}_*` tables:

```typescript
// In manifest:
permissions: {
  tables: {
    write: ["sys_plugin_my_plugin_config", "sys_plugin_my_plugin_data"],
  },
}

// In code:
await sdk.execute(`
  INSERT INTO sys_plugin_my_plugin_data (id, value)
  VALUES ('abc', 42)
`);
```

Attempting to write to unauthorized tables will throw an error.

## Svelte Components

Plugins use Svelte 5 with runes:

```svelte
<script lang="ts">
  import type { PluginSDK } from "./types";

  interface Props {
    sdk: PluginSDK;
  }
  let { sdk }: Props = $props();

  let count = $state(0);
  let theme = $state(sdk.theme.current());

  function increment() {
    count++;
    sdk.toast.info(`Count is now ${count}`);
  }
</script>

<div class:dark={theme === "dark"}>
  <h1>Count: {count}</h1>
  <button onclick={increment}>Increment</button>
</div>

<style>
  div {
    padding: 24px;
    background: white;
    color: black;
  }
  div.dark {
    background: #1a1a1a;
    color: #e5e5e5;
  }
</style>
```

### Styling

Use scoped `<style>` blocks in your Svelte components. To support both light and dark themes, use the theme from SDK:

```svelte
<script lang="ts">
  let theme = $state(sdk.theme.current());
  sdk.theme.subscribe(t => theme = t);
</script>

<div class:dark={theme === "dark"}>
  <!-- content -->
</div>
```

## Tips

- **Keep plugins lightweight** - Users should be able to load multiple plugins without performance issues
- **Handle errors gracefully** - Use try/catch and show errors with `sdk.toast.error()`
- **Support both themes** - Test in light and dark mode
- **Use TypeScript** - Get better IDE support and catch errors early
- **Test thoroughly** - Make sure your plugin works before publishing

## Troubleshooting

### Plugin not loading

1. Check the browser console for errors (open DevTools with Cmd+Option+I)
2. Verify `manifest.json` is valid JSON
3. Ensure `dist/index.js` exists after building
4. Check that the plugin is in `~/.treeline/plugins/your-plugin-id/`

### Build errors

1. Run `npm install` to ensure dependencies are installed
2. Check that TypeScript types are correct
3. Make sure Svelte components have valid syntax

### SDK not available

Make sure you're receiving `sdk` via props:

```svelte
<script lang="ts">
  interface Props {
    sdk: PluginSDK;
  }
  let { sdk }: Props = $props();
</script>
```

### Database permission errors

Check that your manifest declares the tables you're trying to write to:

```typescript
permissions: {
  tables: {
    write: ["sys_plugin_your_plugin_tablename"],
  },
}
```

## Distribution

Once your plugin is ready, you can distribute it by:

1. **GitHub repository** - Users can clone and build
2. **Pre-built releases** - Attach `manifest.json` and `dist/index.js` to GitHub releases
3. **Community registry** - Submit a PR to add your plugin to the Treeline community plugins list

## Next Steps

- Browse the example plugin in this template
- Check out community plugins for inspiration
- Share your plugin with other users!
