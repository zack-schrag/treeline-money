# Treeline Plugin Development

This is a Treeline plugin. Treeline is a local-first personal finance app.

## Key Files

| File | Purpose |
|------|---------|
| `manifest.json` | Plugin metadata (id, name, version, permissions) |
| `src/index.ts` | Plugin entry point - registers views and commands |
| `src/*View.svelte` | Svelte 5 components for your UI |
| `src/types.ts` | TypeScript types for the Plugin SDK |

## Quick Commands

```bash
npm install          # Install dependencies
npm run build        # Build to dist/index.js
npm run dev          # Watch mode (rebuild on changes)
tl plugin install .  # Install locally for testing
```

## SDK Quick Reference

Views receive `sdk` via props:

```svelte
<script lang="ts">
  import type { PluginSDK } from "./types";
  let { sdk }: { sdk: PluginSDK } = $props();
</script>
```

| Method | What it does |
|--------|--------------|
| `sdk.query(sql)` | Read data (SELECT queries) |
| `sdk.execute(sql)` | Write to your plugin's tables only |
| `sdk.toast.success/error/info(msg)` | Show notifications |
| `sdk.openView(viewId, props?)` | Navigate to another view |
| `sdk.onDataRefresh(callback)` | React when data changes (sync/import) |
| `sdk.theme.current()` | Get "light" or "dark" |
| `sdk.settings.get/set()` | Persist plugin settings |

## Database Access

- **Read anything**: `sdk.query("SELECT * FROM transactions")`
- **Write only to your tables**: Must be declared in `manifest.json` permissions
- **Table naming**: Use `sys_plugin_{your_plugin_id}_*` for your tables

## Common Patterns

### Create a table for your plugin data
```typescript
await sdk.execute(`
  CREATE TABLE IF NOT EXISTS sys_plugin_my_plugin_data (
    id VARCHAR PRIMARY KEY,
    value INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )
`);
```

### Subscribe to theme changes
```typescript
let theme = $state(sdk.theme.current());
sdk.theme.subscribe(t => theme = t);
```

### Show loading state
```typescript
let isLoading = $state(true);
try {
  const data = await sdk.query("SELECT ...");
  // use data
} finally {
  isLoading = false;
}
```

## Icons

Use Lucide icon names for sidebar items and views:

```typescript
icon: "target"   // Preferred - icon name
icon: "🎯"       // Also works - emoji
```

**Available icons:** `target`, `repeat`, `shield`, `bank`, `wallet`, `credit-card`, `chart`, `tag`, `tags`, `database`, `refresh`, `link`, `zap`, `calendar`, `file-text`, `settings`, `plus`, `search`, `check`, `x`, `alert-triangle`, `info`, `help-circle`

## Don't Do

- Don't write to tables not in your permissions (will throw error)
- Don't forget dark mode support (test with both themes)
- Don't bundle heavy dependencies (keep plugins lightweight)
- Don't use `sdk.execute()` for SELECT queries (use `sdk.query()`)

## Releasing

```bash
./scripts/release.sh 0.1.0   # Tags and pushes, GitHub Action creates release
```

## Full Documentation

See https://github.com/zack-schrag/treeline-money/blob/main/docs/plugins.md
