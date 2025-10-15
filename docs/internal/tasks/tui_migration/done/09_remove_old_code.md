# Task 09: Remove All Old Code

## Priority
**CRITICAL** - Final cleanup, no leftovers

## Objective
Remove ALL old REPL code, slash command handlers, and unused files. Leave only the new Typer + Textual architecture.

## Files to Delete

### REPL Infrastructure
- [ ] `run_interactive_mode()` function in cli.py
- [ ] `process_command()` function in cli.py
- [ ] `SlashCommandCompleter` class in cli.py
- [ ] All slash command parsing logic
- [ ] `SLASH_COMMANDS` list

### Old Command Handlers
- [ ] `commands/query.py` - Replaced by analysis TUI
- [ ] `commands/tag.py` - Replaced by tag_textual.py
- [ ] `commands/chart.py` - Replaced by charts_textual.py
- [ ] `commands/saved_queries.py` show/list handlers - Keep only helper functions
- [ ] Any other old command files

### Unused Imports
- [ ] Remove unused imports from cli.py
- [ ] Clean up any remaining slash command references

## Code to Keep

### In cli.py
```python
# KEEP THESE:
- Typer app definition
- All @app.command() definitions
- Helper functions: require_auth(), get_authenticated_user_id(), etc.
- Display functions: display_error(), output_json(), etc.
- Container/dependency injection code

# DELETE THESE:
- run_interactive_mode()
- process_command()
- SlashCommandCompleter
- show_welcome_message() (if REPL-specific)
- prompt_for_file_path() (if unused)
```

### In commands/
```python
# KEEP:
- analysis_textual.py
- tag_textual.py
- queries_textual.py
- charts_textual.py
- chart_wizard.py (helper)
- chart_config.py (helper functions only)
- saved_queries.py (helper functions only)

# DELETE:
- analysis.py (old prompt_toolkit version)
- query.py (old SQL editor)
- tag.py (old implementation)
- chart.py (old implementation)
- Any other old implementations
```

## Verification Steps

1. **Search for dead code:**
```bash
grep -r "/status" src/
grep -r "/sync" src/
grep -r "/analysis" src/
# Should find NO slash command references
```

2. **Verify no prompt_toolkit imports:**
```bash
grep -r "from prompt_toolkit" src/
# Should only find in old files (if any remain)
```

3. **Check for unused functions:**
- Review cli.py for any orphaned functions
- Look for functions only used by old REPL

4. **Test all commands:**
```bash
treeline --help
treeline status
treeline sync
treeline analysis
treeline tag
treeline chat
# etc.
```

5. **Run architecture guardian:**
```bash
# Use architecture-guardian agent to verify no violations
```

## Update Documentation

- [ ] Update README.md with new command structure
- [ ] Update CLAUDE.md if needed
- [ ] Remove references to slash commands
- [ ] Update any user-facing docs

## Success Criteria
- [ ] No slash command code remains
- [ ] No old REPL infrastructure
- [ ] All commands work via `treeline <command>`
- [ ] `treeline legacy` removed
- [ ] Clean git diff showing deletions
- [ ] All tests pass
- [ ] Architecture guardian passes

## Files to Modify
- `src/treeline/cli.py` - Major cleanup
- `README.md` - Update examples
- `CLAUDE.md` - Update if needed

## Files to Delete
See list above - should be significant LOC reduction

## Risk Mitigation
- Create git branch before this task
- Review diff carefully
- Test thoroughly
- Keep one commit so it's easily reversible
