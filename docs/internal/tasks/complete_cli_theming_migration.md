## Complete CLI Theming Migration - Final 4 Files

The theme infrastructure is complete and 6 out of 10 files have been refactored to use the theme system.

### ✅ Completed Files (6/10):
1. ✅ `src/treeline/cli.py` - Main CLI entry point
2. ✅ `src/treeline/commands/status.py` - Status command
3. ✅ `src/treeline/commands/sync.py` - Sync command
4. ✅ `src/treeline/commands/simplefin.py` - SimpleFIN setup
5. ✅ `src/treeline/commands/login.py` - Login/signup
6. ✅ `src/treeline/commands/help.py` - Help command

### ⏳ Remaining Files (4/10):

1. **`src/treeline/commands/query.py`** (~11 occurrences)
2. **`src/treeline/commands/chat.py`** (~7 occurrences)
3. **`src/treeline/commands/tag.py`** (~20 occurrences)
4. **`src/treeline/commands/import_csv.py`** (~48 occurrences)

Total remaining: ~86 color occurrences

### Pattern to Follow

See completed files for examples. The pattern is:

1. Add imports at top:
```python
from treeline.theme import get_theme

theme = get_theme()
```

2. Replace hardcoded colors with theme properties:
```python
# Before:
console.print("[red]Error message[/red]")
console.print("[green]✓[/green] Success")
console.print("[bold cyan]Header[/bold cyan]")
console.print("[dim]Muted text[/dim]")

# After:
console.print(f"[{theme.error}]Error message[/{theme.error}]")
console.print(f"[{theme.success}]✓[/{theme.success}] Success")
console.print(f"[{theme.ui_header}]Header[/{theme.ui_header}]")
console.print(f"[{theme.muted}]Muted text[/{theme.muted}]")
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
- Table styles: Use `theme.info`, `theme.ui_value`, `theme.ui_selected`, etc.

### Acceptance Criteria

- All 4 remaining files refactored to use theme system
- No hardcoded color strings remain in command files
- All unit tests still passing (currently 132/132 passing)
- Manual testing confirms colors display correctly
- Consider adding a second theme file (e.g., "minimal" or "high-contrast") to prove customization works

### Testing

After refactoring, test each command:
- `/query SELECT * FROM transactions LIMIT 5`
- Natural language chat
- `/tag` (interactive mode)
- `/import` (with a sample CSV)

### Progress

- **Infrastructure**: ✅ 100% complete (Theme class, JSON, tests)
- **File Migration**: 🔄 60% complete (6/10 files done)
- **Total Colors**: 🔄 42% migrated (~62/148 occurrences done)

The theming system is fully functional. The remaining work is straightforward refactoring following the established pattern.
