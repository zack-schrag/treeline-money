# Task 10: Final Validation and Documentation

## Priority
**CRITICAL** - Ensure quality and completeness

## Objective
Comprehensive testing, documentation update, and final architecture validation.

## Testing Checklist

### Functional Testing
- [ ] All commands: `treeline <cmd> --help` shows help
- [ ] Status: `treeline status` and `treeline status --json`
- [ ] Sync: `treeline sync` and `treeline sync --json`
- [ ] Import: `treeline import <file>`
- [ ] Query: `treeline query "SELECT ..."` with --json and --format
- [ ] Schema: `treeline schema` and `treeline schema accounts`
- [ ] Analysis TUI: All features work (query, chart, save, load)
- [ ] Tag TUI: All features work (navigate, edit, suggest, save)
- [ ] Queries TUI: Browse, load, delete, rename
- [ ] Charts TUI: Browse, load, delete, rename
- [ ] Chat: Interactive conversation maintains context
- [ ] Ask: One-shot queries work
- [ ] Login: Authentication flow
- [ ] Setup: Integration setup wizard

### Scriptability Testing
```bash
# Test piping
treeline status --json | jq .total_transactions
treeline query "SELECT * FROM accounts" --json | jq '.'

# Test redirection
treeline query "SELECT * FROM transactions" --format csv > transactions.csv
treeline status --json > status.json

# Test in scripts
./scripts/daily_sync.sh  # Should use treeline commands
```

### Architecture Validation
- [ ] Run architecture-guardian agent
- [ ] Verify no business logic in CLI
- [ ] Verify all business logic in services
- [ ] No direct infra/ imports in CLI
- [ ] Container pattern used everywhere
- [ ] Storage abstractions used correctly

### Error Handling
- [ ] Not authenticated errors handled gracefully
- [ ] Invalid SQL queries show clear errors
- [ ] File not found errors are user-friendly
- [ ] Network errors handled properly
- [ ] All errors exit with non-zero code

### Performance
- [ ] Commands start quickly (<500ms)
- [ ] TUI apps launch smoothly
- [ ] Large datasets handled well
- [ ] No memory leaks in long-running TUIs

## Documentation Updates

### README.md
Update with:
- New command structure
- Installation instructions
- Quick start guide
- Command reference
- Remove slash command references

### Example:
```markdown
# Quick Start

## Installation
```bash
pip install treeline-cli
```

## Basic Commands
```bash
treeline login                           # Authenticate
treeline status                          # Show summary
treeline sync                            # Sync data
treeline analysis                        # Launch analysis TUI
treeline query "SELECT * FROM accounts"  # Run SQL query
```

## Scripting
```bash
# Get transaction count
treeline status --json | jq .total_transactions

# Export to CSV
treeline query "SELECT * FROM transactions" --format csv > data.csv
```
```

### CLAUDE.md
- [ ] Update to reflect new CLI structure
- [ ] Add TUI development guidelines
- [ ] Document Typer command patterns
- [ ] Update testing instructions

### docs/external/
- [ ] Update user guide
- [ ] Add command reference
- [ ] Add scripting examples
- [ ] Add TUI screenshots/demos

## Metrics

Track improvements:
```
Lines of Code:
- Before: ____ lines
- After:  ____ lines
- Reduction: ____%

Command Structure:
- Before: Slash commands (unconventional)
- After: Standard CLI (git-like)

Scriptability:
- Before: Not scriptable
- After: Fully scriptable with --json

TUI Consistency:
- Before: Mixed (Rich + prompt_toolkit)
- After: Consistent (Textual)

Architecture Violations:
- Before: ___ violations
- After: 0 violations
```

## Final Checklist

### Code Quality
- [ ] All tests passing (unit + smoke)
- [ ] No linting errors
- [ ] No type errors
- [ ] No architectural violations
- [ ] Code coverage maintained/improved

### User Experience
- [ ] Commands are discoverable
- [ ] Help text is clear and useful
- [ ] Error messages are actionable
- [ ] TUIs feel polished
- [ ] Performance is acceptable

### Documentation
- [ ] README updated
- [ ] CLAUDE.md updated
- [ ] User guide updated
- [ ] Examples provided
- [ ] Migration notes (if needed)

### Git
- [ ] Clean commit history
- [ ] Descriptive commit messages
- [ ] No leftover debug code
- [ ] No commented-out code
- [ ] Branch merged to main

## Success Criteria
- [ ] All commands working
- [ ] Zero architectural violations
- [ ] Documentation complete
- [ ] Tests passing
- [ ] Ready for user testing
- [ ] Migration complete - NO old code remains

## Deliverables
1. Working treeline CLI with new structure
2. Updated documentation
3. Test reports
4. Architecture validation report
5. Migration summary document
