## Complete CLI Theming Migration

The theme infrastructure has been implemented with:
- Theme class and JSON-based theme system (`src/treeline/theme.py`)
- Default theme file (`src/treeline/themes/default.json`)
- Unit tests for theme loading and validation
- Example refactoring in `status.py`

**Remaining Work**: Systematically refactor hardcoded colors in remaining files to use the theme system.

### Files Needing Refactoring

The following files still have hardcoded Rich markup colors:

1. `src/treeline/cli.py` - ~23 occurrences
2. `src/treeline/commands/tag.py` - ~20 occurrences
3. `src/treeline/commands/import_csv.py` - ~48 occurrences
4. `src/treeline/commands/sync.py` - ~16 occurrences
5. `src/treeline/commands/simplefin.py` - ~9 occurrences
6. `src/treeline/commands/query.py` - ~11 occurrences
7. `src/treeline/commands/login.py` - ~7 occurrences
8. `src/treeline/commands/chat.py` - ~7 occurrences

Total: ~141 occurrences remaining

### Pattern to Follow

See `src/treeline/commands/status.py` for the complete example. The pattern is:

1. Add import at top:
```python
from treeline.theme import get_theme

theme = get_theme()
```

2. Replace hardcoded colors with theme properties:
```python
# Before:
console.print("[red]Error message[/red]")
console.print("[bold cyan]Header[/bold cyan]")

# After:
console.print(f"[{theme.error}]Error message[/{theme.error}]")
console.print(f"[{theme.ui_header}]Header[/{theme.ui_header}]")
```

3. Common mappings:
- `[red]` → `theme.error`
- `[green]` → `theme.success`
- `[yellow]` → `theme.warning`
- `[cyan]` or `[blue]` → `theme.info`
- `[dim]` → `theme.muted`
- `[bold]` → `theme.emphasis`
- `[bold cyan]` → `theme.ui_header`
- Money amounts: Use `theme.positive_amount` or `theme.negative_amount`

### Acceptance Criteria

- All 8 files refactored to use theme system
- No hardcoded color strings in command files
- All 132+ unit tests still passing
- Manual testing confirms colors display correctly
- Consider adding a second theme (e.g., "minimal" or "high-contrast") to prove the system works

### Notes

- This is purely refactoring - no functional changes
- Rich markup syntax stays the same, just using theme properties
- If a color combo doesn't exist in theme, add it to the theme JSON first
