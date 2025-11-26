# Treeline UI

A plugin-based desktop UI for Treeline personal finance. The core is intentionally minimal—**everything is a plugin**.

## Quick Start

```bash
cd ui
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Core Shell                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ Sidebar │  │ Tab Bar │  │ Content │  │ Command Palette │ │
│  │(plugins)│  │(plugins)│  │  Area   │  │    (plugins)    │ │
│  └─────────┘  └─────────┘  │(plugins)│  └─────────────────┘ │
│                            └─────────┘                      │
├─────────────────────────────────────────────────────────────┤
│                       Plugin SDK                            │
│  • registerView()      • registerCommand()                  │
│  • registerSidebarItem() • db.query()                       │
│  • Theme system        • Event subscriptions                │
├─────────────────────────────────────────────────────────────┤
│                         Plugins                             │
│  ┌────────────┐ ┌──────────┐ ┌───────┐ ┌─────────────────┐  │
│  │Transactions│ │ Accounts │ │ Query │ │    Net Worth    │  │
│  └────────────┘ └──────────┘ └───────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Concepts

### The Shell

The shell is **extremely minimal**. It only provides:

- Window frame
- Sidebar (populated BY plugins)
- Tab system (tabs come FROM plugins)
- Command palette (discovers commands FROM plugins)
- Theme engine
- Plugin loader

No views, no business logic. Everything else is a plugin.

### Plugins

A plugin can:

1. **Register views** - Svelte components that render in tabs
2. **Register sidebar items** - Navigation entries
3. **Register commands** - Actions for command palette
4. **Register status bar items** - Footer widgets
5. **Access database** - Query the DuckDB database
6. **Respond to theme changes** - Adapt to user preferences

### Theme System

Themes are CSS variable-based. Built-in themes:

- `dark` (default) - GitHub dark style
- `light` - Clean light theme
- `nord` - Nord color scheme

Click the theme button in the status bar to cycle through themes.

## Creating a Plugin

### 1. Create Plugin Directory

```
src/lib/plugins/my-plugin/
├── index.ts              # Plugin definition
├── MyView.svelte         # Main view component
└── components/           # Optional sub-components
```

### 2. Define the Plugin

```typescript
// src/lib/plugins/my-plugin/index.ts
import type { Plugin, PluginContext } from "../../sdk/types";
import MyView from "./MyView.svelte";

export const myPlugin: Plugin = {
  manifest: {
    id: "my-plugin",
    name: "My Plugin",
    version: "1.0.0",
    description: "Does something cool",
    author: "Your Name",
    icon: "🚀",
  },

  activate(ctx: PluginContext) {
    // Register a view
    ctx.registerView({
      id: "my-view",
      name: "My View",
      icon: "🚀",
      component: MyView,
    });

    // Add to sidebar
    ctx.registerSidebarItem({
      id: "my-plugin-nav",
      label: "My Plugin",
      icon: "🚀",
      sectionId: "plugins", // or "core", "views"
      viewId: "my-view",
    });

    // Add a command
    ctx.registerCommand({
      id: "my-plugin:action",
      name: "Do Something",
      category: "My Plugin",
      shortcut: "⌘⇧M",
      execute: () => {
        // Do something
      },
    });
  },
};
```

### 3. Create the View

```svelte
<!-- src/lib/plugins/my-plugin/MyView.svelte -->
<script lang="ts">
  import { createMockDatabase } from "../../sdk/db";

  const db = createMockDatabase();
  let data = $state([]);

  async function loadData() {
    data = await db.query("SELECT * FROM transactions LIMIT 10");
  }
</script>

<div class="my-view">
  <h1>My Plugin</h1>
  <button onclick={loadData}>Load Data</button>

  {#each data as item}
    <div>{item.description}</div>
  {/each}
</div>

<style>
  .my-view {
    padding: var(--spacing-lg);
    background: var(--bg-primary);
    color: var(--text-primary);
  }
</style>
```

### 4. Register the Plugin

Add to `src/lib/plugins/index.ts`:

```typescript
import { myPlugin } from "./my-plugin";

const corePlugins: Plugin[] = [
  // ... existing plugins
  myPlugin,
];
```

## Plugin Database Access

Plugins query data using SQL:

```typescript
// Read data
const transactions = await ctx.db.query(`
  SELECT * FROM transactions
  WHERE amount < -100
  ORDER BY transaction_date DESC
`);

// Write to plugin tables (namespaced)
await ctx.db.execute(`
  INSERT INTO plugin_myplug_settings (key, value)
  VALUES ('theme', 'dark')
`);

// Run migrations
await ctx.db.migrate("my-plugin", [
  {
    version: 1,
    description: "Create settings table",
    sql: `CREATE TABLE plugin_myplug_settings (
      key TEXT PRIMARY KEY,
      value TEXT
    )`,
  },
]);
```

### Database Rules

- ✅ **CAN** read from any core table
- ✅ **CAN** create tables with `plugin_<id>_` prefix
- ❌ **CANNOT** modify core tables
- ❌ **CANNOT** access other plugins' tables directly

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘K` | Open command palette |
| `⌘1-9` | Switch to tab 1-9 |
| `⌘W` | Close current tab |
| `/` | Focus search (in views) |

## Project Structure

```
ui/
├── src/
│   ├── lib/
│   │   ├── core/           # Shell components (minimal!)
│   │   │   ├── Shell.svelte
│   │   │   ├── Sidebar.svelte
│   │   │   ├── TabBar.svelte
│   │   │   ├── ContentArea.svelte
│   │   │   ├── CommandPalette.svelte
│   │   │   └── StatusBar.svelte
│   │   │
│   │   ├── sdk/            # Plugin SDK
│   │   │   ├── types.ts    # Type definitions
│   │   │   ├── registry.ts # Plugin state management
│   │   │   ├── db.ts       # Database interface
│   │   │   ├── theme.ts    # Theme system
│   │   │   └── index.ts    # Public exports
│   │   │
│   │   ├── plugins/        # All plugins (core + community)
│   │   │   ├── transactions/
│   │   │   ├── accounts/
│   │   │   ├── query/
│   │   │   ├── net-worth/
│   │   │   └── index.ts    # Plugin loader
│   │   │
│   │   └── themes/         # Theme definitions
│   │
│   ├── App.svelte          # Root component
│   ├── app.css             # Global styles
│   └── main.ts             # Entry point
│
├── package.json
└── vite.config.ts
```

## Design Philosophy

- **IDE-like, not cute** - Dense, keyboard-driven, power-user focused
- **SQL is the API** - Query your data directly, no REST endpoints needed
- **Local-first** - Your data stays on your machine (DuckDB file)
- **Extensible** - Everything beyond the shell is a plugin
- **Themeable** - Full CSS variable system for customization

## Future: Tauri Integration

For the desktop app, we'll use Tauri to:

1. Wrap the web UI in a native window
2. Provide DuckDB access via Rust bindings
3. Run Python sidecar for sync operations
4. Handle file system access

The current prototype uses mock data, but the plugin interface is designed for real database access.
