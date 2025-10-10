# Simplify /sql Post-Execution Prompts

## Problem

After query execution in `/sql`, users face too many sequential prompts:
1. "Create a chart?" (y/n)
2. [If yes, full chart wizard]
3. "Save this query?" (y/n)
4. "Continue editing?" (y/n)

This creates friction and breaks flow. Users should have a **single** decision point.

## Solution

Replace sequential prompts with a **single action menu**:

```
[Results displayed]

100 rows returned

Next? [c]hart  [s]ave  [e]dit  [enter] to continue
>
```

- Single keypress navigation
- `c` - opens chart wizard
- `s` - saves query
- `e` - loops back to SQL editor
- `enter` - exits cleanly (no more "continue editing?" prompt)

## Implementation Details

### Changes to `query.py`

**Current:**
```python
# Prompt to create chart
_prompt_chart_wizard(sql_stripped, columns, rows)

# Prompt to save query, and loop back if requested
if loop_back_handler:
    _prompt_to_save_query_with_loopback(sql_stripped, loop_back_handler)
else:
    _prompt_to_save_query(sql_stripped)
```

**New:**
```python
# Single action menu
_prompt_post_query_actions(sql_stripped, columns, rows, loop_back_handler)
```

### New Function

```python
def _prompt_post_query_actions(
    sql: str,
    columns: list[str],
    rows: list[list],
    loop_back_handler=None
) -> None:
    """Prompt user for next action after query execution.

    Args:
        sql: The SQL query that was executed
        columns: Column names from results
        rows: Query result rows
        loop_back_handler: Optional callback to return to SQL editor
    """
    try:
        while True:
            console.print()
            action = Prompt.ask(
                f"[{theme.info}]Next?[/{theme.info}] [c]hart  [s]ave  [e]dit  [enter] to continue",
                default="",
                show_default=False
            )

            if action == "":
                # Enter pressed - exit cleanly
                return
            elif action.lower() == "c":
                # Chart wizard
                _prompt_chart_wizard(sql, columns, rows)
                # After charting, continue loop (can save or edit)
            elif action.lower() == "s":
                # Save query
                _prompt_to_save_query(sql)
                return
            elif action.lower() == "e":
                # Edit SQL - loop back
                if loop_back_handler:
                    loop_back_handler()
                return
            else:
                console.print(f"[{theme.error}]Invalid option. Use c/s/e or press enter[/{theme.error}]")

    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.muted}]Exiting[/{theme.muted}]\n")
```

### Chart Wizard Simplification

Since chart wizard is now invoked from action menu, it should NOT ask "save chart?" at the end - that happens separately in the action menu loop.

Update `_prompt_chart_wizard` to:
1. Guide through chart creation
2. Display chart
3. Optionally save chart config
4. Return (back to action menu)

## Testing

### Unit Tests

Create `tests/unit/commands/test_post_query_actions.py`:

```python
def test_action_menu_chart_flow():
    """Test selecting chart from action menu."""
    # Mock user input: 'c' then ''
    # Verify chart wizard is called
    # Verify clean exit after

def test_action_menu_save_flow():
    """Test selecting save from action menu."""
    # Mock user input: 's'
    # Verify save query is called

def test_action_menu_edit_flow():
    """Test selecting edit from action menu."""
    # Mock user input: 'e'
    # Verify loop_back_handler is called

def test_action_menu_enter_exits():
    """Test pressing enter exits cleanly."""
    # Mock user input: ''
    # Verify clean exit, no prompts
```

### Manual Testing

```bash
> /sql
>: SELECT * FROM transactions LIMIT 10

[Results]

Next? [c]hart  [s]ave  [e]dit  [enter] to continue
> c

[Chart wizard runs]

Next? [c]hart  [s]ave  [e]dit  [enter] to continue
> s

Query name: test_query
✓ Saved

> [clean exit]
```

## Acceptance Criteria

- [ ] Single action menu replaces all post-query prompts
- [ ] `c` opens chart wizard
- [ ] `s` saves query
- [ ] `e` loops back to SQL editor
- [ ] `enter` exits cleanly without additional prompts
- [ ] Action menu loops after chart creation (can save/edit afterward)
- [ ] Chart wizard no longer has separate "save?" prompt
- [ ] Unit tests for action menu flow
- [ ] Existing `/sql` tests still pass

## Notes

- This is a quick win that reduces friction immediately
- Maintains all existing functionality, just better UX
- Sets foundation for `/analysis` mode (similar action menu pattern)
