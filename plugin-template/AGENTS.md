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

## Database Access & Permissions

Plugins must declare all table permissions in `manifest.json`:

```json
{
  "permissions": {
    "tables": {
      "read": ["transactions", "accounts"],  // Tables you can SELECT from
      "create": ["sys_plugin_my_plugin"]     // Tables you can CREATE/DROP (implicitly writable)
    }
  }
}
```

| Permission | Description |
|------------|-------------|
| `read` | Tables your plugin can SELECT from. Required - no implicit access. Use `["*"]` for all tables. |
| `write` | Tables you can INSERT/UPDATE/DELETE (but not create). Rarely needed. |
| `create` | Tables you can CREATE/DROP. Must match `sys_plugin_{id}_*` pattern. Implicitly writable. |

- **Table naming**: Your tables must use `sys_plugin_{your_plugin_id}_*` pattern
- **Core tables**: Common readable tables include `transactions`, `accounts`, `sys_balance_snapshots`
- **Cross-plugin reads**: You can read other plugins' tables if declared (e.g., `sys_plugin_goals`)

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

**Available icons:** `activity`, `trending-up`, `target`, `repeat`, `shield`, `bank`, `wallet`, `credit-card`, `chart`, `tag`, `tags`, `database`, `refresh`, `link`, `zap`, `calendar`, `file-text`, `settings`, `plus`, `search`, `check`, `x`, `alert-triangle`, `info`, `help-circle`

## Styling

### Form Select Dropdowns
All `<select>` elements MUST use this styling pattern for consistent appearance:

```css
select {
  padding: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 13px;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 28px;
  cursor: pointer;
}

select:focus {
  outline: none;
  border-color: var(--accent-primary);
}

select option {
  background: var(--bg-secondary);
  color: var(--text-primary);
  padding: 8px;
}
```

**Key requirements:**
- `appearance: none` removes native browser styling
- Custom SVG arrow via `background-image`
- `padding-right: 28px` makes room for the arrow
- Style `option` elements for dropdown menu consistency

### CSS Variables
Always use theme CSS variables:
- `--bg-primary`, `--bg-secondary`, `--bg-tertiary` - Backgrounds
- `--text-primary`, `--text-secondary`, `--text-muted` - Text
- `--border-primary` - Borders
- `--accent-primary`, `--accent-success`, `--accent-danger` - Accents
- `--spacing-xs/sm/md/lg/xl` - Spacing
- `--radius-sm/md/lg` - Border radius

## Don't Do

- Don't read from tables not declared in your `read` permissions (will throw error)
- Don't write to tables not in your permissions (will throw error)
- Don't create tables that don't match `sys_plugin_{your_id}_*` pattern
- Don't forget dark mode support (test with both themes)
- Don't bundle heavy dependencies (keep plugins lightweight)
- Don't use `sdk.execute()` for SELECT queries (use `sdk.query()`)
- Don't use native select styling (always use the pattern above)

## Releasing

```bash
./scripts/release.sh 0.1.0   # Tags and pushes, GitHub Action creates release
```

## Full Documentation

See https://github.com/zack-schrag/treeline-money/blob/main/docs/plugins.md
