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
