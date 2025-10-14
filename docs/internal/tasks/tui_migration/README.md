# TUI Migration Plan

## Objective
Migrate from REPL-based slash commands (`/status`, `/sync`) to standard CLI architecture (`treeline status`, `treeline sync`) with Textual TUIs for complex workflows.

## Why This Migration?

**Current Problems:**
- Slash commands are non-standard (not discoverable)
- Not scriptable or automatable
- Can't compose with Unix tools
- Difficult to document
- Mixed responsibilities between CLI and service layers

**Benefits of New Architecture:**
- Industry-standard CLI patterns (like git, docker, kubectl)
- Scriptable and automatable (CI/CD, cron jobs)
- Composable with Unix tools (pipe, redirect)
- Discoverable (`treeline --help`)
- Clear separation: simple=CLI, complex=TUI
- Professional feel

## Architecture Overview

### Command Categories

**1. Scriptable Commands** (Output to stdout, composable)
- `treeline status` - Show account summary
- `treeline sync` - Sync integrations
- `treeline import <file>` - Import CSV
- `treeline query "SELECT..."` - Execute SQL
- `treeline schema [table]` - Show database schema

**2. TUI Commands** (Full-screen interactive Textual apps)
- `treeline analysis` - Interactive data exploration
- `treeline tag` - Tag transactions interactively
- `treeline charts` - Browse/manage saved charts
- `treeline queries` - Browse/manage saved queries

**3. Hybrid Commands** (Can be both)
- `treeline chat` - Interactive AI REPL
- `treeline ask "question"` - One-shot AI query

### New CLI Structure

```
treeline [command] [args] [options]

Commands:
  status              Show account summary (scriptable)
  sync                Sync all integrations (scriptable)
  import <file>       Import transactions from CSV (scriptable)
  query "SQL"         Execute SQL query (scriptable)
  schema [table]      Show database schema (scriptable)

  analysis            Launch analysis TUI (interactive)
  tag                 Launch tagging TUI (interactive)
  charts              Browse saved charts (interactive)
  queries             Browse saved queries (interactive)

  chat                Start AI conversation (interactive)
  ask "question"      Ask AI a question (scriptable)

  login               Authenticate with Supabase
  init                Initialize treeline in current directory

Options:
  --help              Show help for command
  --json              Output as JSON (scriptable commands)
  --version           Show version
```

## Migration Strategy

### Phase 1: Foundation (Tasks 01-02)
Create new CLI structure, migrate one of each type for validation

### Phase 2: Review (Milestone)
Review look & feel with user, validate architecture

### Phase 3: Scriptable Commands (Tasks 03-05)
Migrate remaining simple commands

### Phase 4: TUI Commands (Tasks 06-08)
Migrate complex interactive commands

### Phase 5: Chat/AI (Task 09)
Migrate AI chat to new structure

### Phase 6: Cleanup (Task 10)
Remove all old code, update docs

## Success Criteria

✅ All commands work as `treeline <command>`
✅ Scriptable commands support `--json` flag
✅ TUI commands use Textual consistently
✅ CLI layer has zero business logic
✅ Service layer has all business logic
✅ Old REPL code completely removed
✅ All tests passing
✅ Documentation updated
✅ Architecture validation passes

## Testing Approach

**Per Command:**
1. Manual testing: `treeline <command> --help`
2. Functional testing: Verify same behavior as old slash command
3. Scripting test: Test `--json` output (if applicable)
4. Architecture review: Verify no business logic in CLI

**Final Validation:**
1. Run full test suite
2. Test common workflows
3. Test scriptability (pipes, redirects)
4. Run architecture-guardian agent
5. User acceptance testing

## Risk Mitigation

- Migrate one at a time, test thoroughly
- Keep old code until replacement is validated
- Review after first two migrations (checkpoint)
- Service layer changes first, CLI second
- Each task is atomic and reversible
