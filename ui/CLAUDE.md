# UI Development Guidelines

## Tech Stack
- **Framework**: Svelte 5 with runes ($state, $derived, $effect)
- **Desktop**: Tauri (Rust backend)
- **Build**: Vite

## Running the App
```bash
npm run tauri:dev   # Development with hot reload
npm run build       # Production build
```

## Styling Conventions

### CSS Variables
Always use CSS variables from the theme:
- `--bg-primary`, `--bg-secondary`, `--bg-tertiary` - Background colors
- `--text-primary`, `--text-secondary`, `--text-muted` - Text colors
- `--border-primary` - Border color
- `--accent-primary` - Primary accent (blue)
- `--accent-success` - Success (green)
- `--accent-danger` - Danger (red)
- `--accent-warning` - Warning (orange)
- `--spacing-xs`, `--spacing-sm`, `--spacing-md`, `--spacing-lg`, `--spacing-xl` - Spacing
- `--font-mono` - Monospace font

### Form Select Dropdowns
All `<select>` elements in modals/forms should use this styling pattern:
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

### Buttons
- `.btn.primary` - Primary action (accent background, white text)
- `.btn.secondary` - Secondary action (tertiary background, border)
- `.btn.danger` - Destructive action (danger color)
- `.btn.text` - Text-only button

### Modal Structure
Modals use the shared `Modal` component from `../../shared`:
```svelte
<Modal open={showModal} title="Title" onclose={closeModal} width="500px">
  <!-- Content -->

  {#snippet actions()}
    <button class="btn secondary" onclick={close}>Cancel</button>
    <button class="btn primary" onclick={save}>Save</button>
  {/snippet}
</Modal>
```

## Component Patterns

### State Management
Use Svelte 5 runes:
```typescript
let value = $state<string>("");
let computed = $derived(value.toUpperCase());
let complexComputed = $derived.by(() => { /* logic */ });
```

### Keyboard Navigation
Most views support vim-style navigation:
- `j/k` or arrows - Navigate up/down
- `Enter` - Select/open
- `e` - Edit
- `d` - Delete
- `a` - Add new

## Database Access
Use `executeQuery` from SDK for DuckDB queries:
```typescript
import { executeQuery } from "../../sdk";

// Read-only (default)
const result = await executeQuery("SELECT * FROM transactions");

// Write operations
await executeQuery("UPDATE sys_transactions SET ...", { readonly: false });
```

**Important**: Use `sys_transactions` (base table) for UPDATE/INSERT, not `transactions` (view).

## UX Philosophy

### Progressive Disclosure
Make the common case easy, but don't restrict power users. Examples:
- Auto-tag rules: Simple "contains/starts with" by default, but "Edit SQL" link for power users
- Budget transfers: Single transfer with defaults, but "+ Add another" to split across categories

### Don't Over-Constrain
Surface helpful indicators (e.g., "Remaining: $20") but don't prevent users from doing what they want. Let them over-allocate, under-allocate, etc. - it's their budget.

### Data Patterns
- Round currency amounts to cents (`Math.round(amount * 100) / 100`) to avoid floating point display errors
- Store config as JSON in plugin files via `invoke("write_plugin_config", ...)`

## Plugin Architecture

### Core Principles
- **Everything is a plugin**: Accounts, Budget, Transactions, Query are all plugins
- **Core plugins use the same SDK as community plugins** - they just declare different table permissions
- **Settings is NOT a plugin** - it's core app functionality in `lib/core/`

### Plugin Types

| Type | Location | Table Access | Distribution |
|------|----------|--------------|--------------|
| Core plugins | `lib/plugins/` | Can declare any tables in manifest | Bundled with app |
| Community plugins | `~/.treeline/plugins/` | Only `sys_plugin_{id}_*` tables | Separate repos, listed in `community-plugins.json` |

### Manifest Permissions
Plugins declare required write tables in their manifest:
```typescript
manifest: {
  id: "budget",
  permissions: {
    tables: {
      write: ["sys_plugin_budget_categories", "sys_plugin_budget_rollovers"],
    },
  },
}
```

All plugins can READ any table. Write access is enforced at runtime in `sdk/public.ts`.

### Plugin SDK (`lib/sdk/public.ts`)
External plugins receive an SDK via props when their views are mounted:
- `sdk.query(sql)` - Read any table
- `sdk.execute(sql)` - Write to allowed tables only
- `sdk.toast.*` - Show notifications
- `sdk.openView()` - Navigate to views
- `sdk.onDataRefresh()` - React to data changes
- `sdk.settings.get/set()` - Plugin-scoped settings
- `sdk.theme.current()` - Theme access

### Creating a Community Plugin
1. Create plugin: `tl plugin new my-plugin`
2. Develop in the generated directory
3. Build: `npm run build`
4. Create a GitHub release with `manifest.json` and `dist/index.js` as release assets
5. Submit PR to add entry to `community-plugins.json`

### Installing Community Plugins
Users can install plugins from:
- **UI**: Settings → Plugins → Community Plugins (browse and install from registry)
- **CLI**: `tl plugin install https://github.com/user/repo` (latest release)
- **CLI with version**: `tl plugin install https://github.com/user/repo --version v1.0.0`

Installation downloads `manifest.json` and `index.js` from GitHub release assets to `~/.treeline/plugins/{id}/`.

### Publishing Plugin Releases
When creating a GitHub release, attach these files as assets:
- `manifest.json` - Plugin metadata
- `index.js` - Built plugin code (from `dist/index.js`)

Example release command:
```bash
npm run build
gh release create v1.0.0 manifest.json dist/index.js --title "v1.0.0" --notes "Release notes"
```

### Core vs Internal SDK
- **Public SDK** (`sdk/public.ts`): What community plugins can access via props
- **Internal imports**: Core plugins can import from `sdk/` directly for things like `registry`, `activityStore`, internal operations

When building new features, prefer making them plugins unless they require internal SDK access (sync, CSV import, demo mode, etc.).
