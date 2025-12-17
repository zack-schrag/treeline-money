# Treeline Plugin SDK

Complete reference for building Treeline plugins.

## Overview

Treeline plugins extend the app with new views, commands, and functionality. Plugins are built with Svelte 5 and TypeScript, compiled to a single JavaScript file, and loaded at runtime.

## Getting Started

```bash
tl plugin new my-plugin    # Create from template
cd my-plugin
npm install
npm run build
tl plugin install .        # Install locally
# Restart Treeline to load
```

## Plugin Structure

```
my-plugin/
├── manifest.json          # Plugin metadata
├── src/
│   ├── index.ts          # Entry point
│   ├── types.ts          # SDK TypeScript definitions
│   └── MyView.svelte     # UI components
├── dist/
│   └── index.js          # Built plugin (generated)
├── scripts/
│   └── release.sh        # Release helper
├── .github/workflows/
│   └── release.yml       # Auto-release on tag
├── AGENTS.md             # AI assistant context
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## Plugin Manifest

Every plugin must have a `manifest.json`:

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "0.1.0",
  "description": "What this plugin does",
  "author": "Your Name",
  "main": "index.js",
  "permissions": {
    "tables": {
      "write": ["sys_plugin_my_plugin"]
    }
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (lowercase, hyphens allowed) |
| `name` | Yes | Display name |
| `version` | Yes | Semantic version (e.g., "1.0.0") |
| `description` | Yes | Short description |
| `author` | Yes | Author name |
| `main` | Yes | Entry point file (always "index.js") |
| `permissions.tables.write` | No | Tables the plugin can write to |

## Entry Point (index.ts)

Your plugin must export a `plugin` object:

```typescript
import type { Plugin, PluginContext } from "./types";
import MyView from "./MyView.svelte";
import { mount, unmount } from "svelte";

export const plugin: Plugin = {
  manifest: {
    id: "my-plugin",
    name: "My Plugin",
    version: "0.1.0",
    description: "What this plugin does",
    author: "Your Name",
    permissions: {
      tables: {
        write: ["sys_plugin_my_plugin"],
      },
    },
  },

  activate(context: PluginContext) {
    // Register a view
    context.registerView({
      id: "my-view",
      name: "My View",
      icon: "📊",
      mount: (target, props) => {
        const instance = mount(MyView, { target, props });
        return () => unmount(instance);
      },
    });

    // Add to sidebar
    context.registerSidebarItem({
      sectionId: "main",
      id: "my-plugin",
      label: "My Plugin",
      icon: "📊",
      viewId: "my-view",
    });
  },

  deactivate() {
    // Optional cleanup
  },
};
```

## PluginContext API

The `context` object passed to `activate()`:

### registerView(view)

Register a view that can be displayed in the main content area.

```typescript
context.registerView({
  id: "my-view",           // Unique view ID
  name: "My View",         // Display name
  icon: "📊",              // Emoji or icon
  mount: (target, props) => {
    // Mount your Svelte component
    const instance = mount(MyComponent, { target, props });
    // Return cleanup function
    return () => unmount(instance);
  },
});
```

### registerSidebarItem(item)

Add an item to the sidebar.

```typescript
context.registerSidebarItem({
  sectionId: "main",       // Which section ("main", "plugins", etc.)
  id: "my-item",           // Unique item ID
  label: "My Plugin",      // Display label
  icon: "📊",              // Emoji or icon
  viewId: "my-view",       // View to open when clicked
});
```

### registerCommand(command)

Register a command (appears in Cmd+P palette).

```typescript
context.registerCommand({
  id: "my-plugin.do-something",
  name: "Do Something",
  description: "Optional description",
  execute: async () => {
    // Command implementation
  },
});
```

### registerSidebarSection(section)

Add a new sidebar section.

```typescript
context.registerSidebarSection({
  id: "my-section",
  title: "My Section",
  order: 100,  // Higher = lower in sidebar
});
```

## Plugin SDK (View Components)

Your Svelte components receive `sdk` via props:

```svelte
<script lang="ts">
  import type { PluginSDK } from "./types";

  interface Props {
    sdk: PluginSDK;
  }
  let { sdk }: Props = $props();
</script>
```

### sdk.query(sql)

Execute a read-only SQL query. Can read any table.

```typescript
const accounts = await sdk.query<Account>("SELECT * FROM sys_accounts");
const total = await sdk.query<{ sum: number }>(
  "SELECT SUM(amount) as sum FROM transactions WHERE tags @> ['groceries']"
);
```

### sdk.execute(sql)

Execute a write query. Only works on tables declared in `permissions.tables.write`.

```typescript
await sdk.execute(`
  CREATE TABLE IF NOT EXISTS sys_plugin_my_plugin (
    id VARCHAR PRIMARY KEY,
    data JSON
  )
`);

await sdk.execute(`
  INSERT INTO sys_plugin_my_plugin (id, data)
  VALUES ('key', '{"value": 42}')
`);
```

**Note:** Attempting to write to unauthorized tables throws an error.

### sdk.toast

Show toast notifications.

```typescript
sdk.toast.success("Saved!", "Your changes have been saved");
sdk.toast.error("Error", "Something went wrong");
sdk.toast.warning("Warning", "This action cannot be undone");
sdk.toast.info("Info", "Did you know?");
sdk.toast.show("Message");  // Default style
```

### sdk.openView(viewId, props?)

Navigate to another view.

```typescript
sdk.openView("transactions");
sdk.openView("query", { initialQuery: "SELECT * FROM transactions" });
```

### sdk.onDataRefresh(callback)

Subscribe to data refresh events (triggered after sync or import).

```typescript
const unsubscribe = sdk.onDataRefresh(() => {
  // Reload your data
  loadData();
});

// Call unsubscribe() in onDestroy to clean up
```

### sdk.emitDataRefresh()

Notify other views that data has changed.

```typescript
await sdk.execute("INSERT INTO ...");
sdk.emitDataRefresh();  // Tell other views to reload
```

### sdk.theme

Access current theme.

```typescript
const theme = sdk.theme.current();  // "light" or "dark"

// Subscribe to changes
const unsubscribe = sdk.theme.subscribe((newTheme) => {
  theme = newTheme;
});
```

### sdk.settings

Persist plugin settings (survives app restart).

```typescript
// Save settings
await sdk.settings.set({ showAdvanced: true, limit: 100 });

// Load settings
const settings = await sdk.settings.get<{ showAdvanced: boolean; limit: number }>();
```

### sdk.state

Ephemeral state (cleared on app restart).

```typescript
await sdk.state.write({ lastQuery: "SELECT ..." });
const state = await sdk.state.read<{ lastQuery: string }>();
```

### sdk.modKey

Platform-aware modifier key.

```typescript
sdk.modKey  // "Cmd" on Mac, "Ctrl" on Windows/Linux
```

### sdk.formatShortcut(shortcut)

Format keyboard shortcut for display.

```typescript
sdk.formatShortcut("Mod+K")  // "⌘K" on Mac, "Ctrl+K" on Windows
```

## Database Tables

Plugins can read all tables. Key tables:

| Table | Description |
|-------|-------------|
| `sys_accounts` | Bank accounts |
| `transactions` | All transactions |
| `sys_balance_snapshots` | Historical balance data |
| `sys_tags` | Available tags |
| `sys_integrations` | Integration settings |

### Transaction Schema

```sql
SELECT
  id,                    -- UUID
  account_id,            -- Foreign key to sys_accounts
  transaction_date,      -- DATE
  posted_date,           -- DATE (nullable)
  amount,                -- DECIMAL (negative = expense)
  description,           -- VARCHAR
  tags,                  -- VARCHAR[] (array of tag names)
  fingerprint,           -- VARCHAR (deduplication key)
  created_at,
  updated_at
FROM transactions
```

### Account Schema

```sql
SELECT
  id,                    -- UUID
  name,                  -- VARCHAR
  institution_name,      -- VARCHAR
  account_type,          -- VARCHAR (checking, savings, credit, etc.)
  currency,              -- VARCHAR (USD, EUR, etc.)
  is_deleted,            -- BOOLEAN
  created_at,
  updated_at
FROM sys_accounts
```

## Svelte 5 Patterns

Plugins use Svelte 5 with runes:

```svelte
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import type { PluginSDK } from "./types";

  let { sdk }: { sdk: PluginSDK } = $props();

  // Reactive state
  let data = $state<Item[]>([]);
  let isLoading = $state(true);
  let theme = $state(sdk.theme.current());

  // Cleanup tracking
  let unsubscribers: (() => void)[] = [];

  onMount(async () => {
    // Subscribe to theme
    unsubscribers.push(sdk.theme.subscribe(t => theme = t));

    // Subscribe to data refresh
    unsubscribers.push(sdk.onDataRefresh(() => loadData()));

    await loadData();
  });

  onDestroy(() => {
    unsubscribers.forEach(fn => fn());
  });

  async function loadData() {
    isLoading = true;
    try {
      data = await sdk.query("SELECT * FROM ...");
    } catch (e) {
      sdk.toast.error("Failed to load", e.message);
    } finally {
      isLoading = false;
    }
  }
</script>

<div class:dark={theme === "dark"}>
  {#if isLoading}
    <p>Loading...</p>
  {:else}
    {#each data as item}
      <div>{item.name}</div>
    {/each}
  {/if}
</div>

<style>
  div { color: #1a1a1a; }
  div.dark { color: #e5e5e5; }
</style>
```

## Styling

Use scoped `<style>` blocks. Always support both themes:

```svelte
<div class:dark={theme === "dark"}>
  <!-- content -->
</div>

<style>
  div {
    background: #ffffff;
    color: #1a1a1a;
  }
  div.dark {
    background: #1a1a1a;
    color: #e5e5e5;
  }
</style>
```

## Releasing

### Automated Releases

The template includes a GitHub Action that creates releases automatically:

1. Update your code
2. Run `./scripts/release.sh 0.1.0`
3. GitHub Action builds and publishes the release

### Manual Releases

If you prefer manual releases:

1. `npm run build`
2. Create a GitHub release
3. Attach `manifest.json` and `dist/index.js` as release assets

## Community Plugins

### Submitting Your Plugin

1. Ensure your plugin has at least one GitHub release with `manifest.json` and `index.js` attached
2. Fork [treeline-money](https://github.com/zack-schrag/treeline-money)
3. Add your plugin to `community-plugins.json`:

```json
{
  "id": "your-plugin-id",
  "name": "Your Plugin Name",
  "description": "Brief description",
  "author": "Your Name",
  "repo": "https://github.com/you/your-plugin"
}
```

4. Open a PR

### Requirements

- Must have a GitHub release with `manifest.json` and `index.js` assets
- Plugin must install and load without errors
- No malicious code

## Troubleshooting

### Plugin not loading

1. Check browser console (Cmd+Option+I) for errors
2. Verify `manifest.json` is valid JSON
3. Ensure `dist/index.js` exists
4. Check plugin is in `~/.treeline/plugins/{plugin-id}/`

### Permission errors

Ensure tables are declared in `manifest.json`:

```json
"permissions": {
  "tables": {
    "write": ["sys_plugin_your_plugin_tablename"]
  }
}
```

### Build errors

1. Run `npm install`
2. Check TypeScript errors in IDE
3. Verify Svelte syntax is correct

### SDK not available

Make sure you're receiving `sdk` via props:

```svelte
<script lang="ts">
  let { sdk }: { sdk: PluginSDK } = $props();
</script>
```
