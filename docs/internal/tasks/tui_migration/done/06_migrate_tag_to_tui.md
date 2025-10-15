# Task 06: Migrate Tag to Textual TUI

## Priority
**HIGH** - Second TUI command, establishes TUI patterns

## Objective
Convert `/tag` from its current implementation to a proper Textual TUI, similar to `/analysis`.

## Current State Analysis

Review `commands/tag.py`:
- Uses Rich tables and prompts (not full TUI)
- Has interactive loops
- Good candidate for Textual conversion

## Textual TUI Design

### Features
1. **Transaction List** - DataTable with:
   - Transaction date, description, amount
   - Current tags displayed inline
   - Cursor selection

2. **Tag Input** - TextArea or Input for:
   - Adding new tags (comma-separated)
   - Removing tags
   - AI suggestions shown as hints

3. **Key Bindings:**
   - `Enter` - Edit tags for selected transaction
   - `a` - AI suggest tags (if enabled)
   - `↑↓` - Navigate transactions
   - `s` - Save changes
   - `?` - Show help
   - `Ctrl+C` - Exit

4. **Status Bar** - Show:
   - Total transactions
   - Tagged/untagged count
   - Current filters

### Implementation Structure

```python
# commands/tag_textual.py

class TaggingScreen(Screen):
    """Main tagging interface."""

    BINDINGS = [
        Binding("enter", "edit_tags", "Edit Tags"),
        Binding("a", "suggest_tags", "AI Suggest"),
        Binding("s", "save", "Save"),
        Binding("?", "show_help", "Help"),
    ]

    def compose(self):
        yield Header()
        yield DataTable(id="transactions")
        yield Footer()

class TagEditScreen(Screen):
    """Modal for editing tags on selected transaction."""

    def __init__(self, transaction, current_tags, suggestions):
        ...

    def compose(self):
        yield Input(id="tag_input", placeholder="tag1, tag2, tag3")
        yield Static("Suggestions: ...")
        yield Horizontal(
            Button("Save", id="save"),
            Button("Cancel", id="cancel")
        )

class TaggingApp(App):
    """Textual app for transaction tagging."""
    ...
```

## Service Layer Requirements

Verify `TaggingService` has:
- `get_untagged_transactions()`
- `get_transactions_for_tagging()` (with filters)
- `update_transaction_tags()`
- `get_suggested_tags()` (AI)

## CLI Command

```python
@app.command(name="tag")
def tag_command(
    untagged_only: bool = typer.Option(False, "--untagged", help="Show only untagged")
) -> None:
    """Launch interactive transaction tagging interface."""
    user_id = get_authenticated_user_id()

    from treeline.commands.tag_textual import TaggingApp
    app = TaggingApp(user_id=user_id, untagged_only=untagged_only)
    app.run()
```

## Success Criteria
- [ ] Textual TUI launches and displays transactions
- [ ] Can navigate with arrow keys
- [ ] Can edit tags on selected transaction
- [ ] AI suggestions work (if AIProvider available)
- [ ] Changes are saved to database
- [ ] Smooth UX (feels like analysis mode)
- [ ] No business logic in TUI code

## Files to Create
- `src/treeline/commands/tag_textual.py`

## Files to Modify
- `src/treeline/cli.py` - Add command
- `src/treeline/app/service.py` - Verify TaggingService

## Files to Mark for Deletion (later)
- `src/treeline/commands/tag.py` (old implementation, task 10)
