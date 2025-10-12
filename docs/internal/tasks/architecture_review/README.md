# Architecture Review Tasks

This directory contains tasks identified during comprehensive architecture reviews of the Treeline Money codebase.

**Review History:**
- Initial review: 2025-10-11
- Second review: 2025-10-11 (after user changes)
- Status: **All issues from initial review remain present**

## Overview

The codebase has a **solid hexagonal architecture foundation** (80%+ compliant), but has **4 critical** and **2 major** violations that need attention. These violations are localized to 2-3 command files and can be fixed systematically.

**Key Findings from Second Review:**
- No issues were resolved between reviews
- All original violations still present in `tag.py` and `import_csv.py`
- The core patterns are established; remaining fixes follow the same approach

## Task Priority

### Critical (Must Fix)
These break hexagonal architecture core principles:

1. **[01_remove_repository_access_tag_command.md](./01_remove_repository_access_tag_command.md)** - CLI bypassing service layer in `tag.py:51,71`
2. **[02_remove_repository_access_import_csv_command.md](./02_remove_repository_access_import_csv_command.md)** - CLI bypassing service layer in `import_csv.py:52,79`
3. **[03_remove_infra_imports_from_tag_command.md](./03_remove_infra_imports_from_tag_command.md)** - CLI importing infrastructure in `tag.py:38`
4. **[04_refactor_csv_specific_methods_to_service.md](./04_refactor_csv_specific_methods_to_service.md)** - Leaky abstraction in `import_csv.py:110,113,137`

**Status (as of 2025-10-11 second review): ALL STILL PRESENT**

### Major (Should Fix)
These create leaky abstractions but don't break core architecture:

5. **[05_fix_session_expired_leaky_abstraction.md](./05_fix_session_expired_leaky_abstraction.md)** - Service calling non-abstracted method in `service.py:651`
6. **[06_reorganize_abstractions_into_directory.md](./06_reorganize_abstractions_into_directory.md)** - Organizational inconsistency

**Status (as of 2025-10-11 second review): ALL STILL PRESENT**

## Recommended Order

### Phase 1: Foundation (Tasks 1-2)
Start with removing repository access from CLI:
1. Task 01 - Create AccountService and remove repository access from tag command
2. Task 02 - Remove repository access from import CSV command (depends on Task 01)

### Phase 2: Infrastructure Decoupling (Tasks 3-4)
Remove infrastructure dependencies from CLI:
3. Task 03 - Move tag suggester construction to Container (depends on Task 01)
4. Task 04 - Refactor CSV-specific methods to ImportService

### Phase 3: Cleanup (Tasks 5-6)
Address remaining abstraction issues:
5. Task 05 - Fix is_session_expired leaky abstraction (independent)
6. Task 06 - Reorganize abstractions directory (independent, do last)

## Dependencies

```
Task 01 (AccountService creation)
  └─→ Task 02 (CSV import uses AccountService)
  └─→ Task 03 (Tag command needs Task 01 completed first)

Task 04 (CSV refactor) - Independent
Task 05 (Session expiration) - Independent
Task 06 (Directory reorg) - Independent, do LAST
```

## Testing Strategy

After each task:
- Run unit tests: `uv run pytest tests/unit`
- Verify command still works manually
- Commit with descriptive message

After all tasks complete:
- Run full unit test suite
- Run smoke tests: `uv run pytest tests/smoke`
- Verify all commands work end-to-end
- NOTE: these smoke tests are actually disabled right now. Ask the user to verify all functionality instead of running smoke tests.

## Architectural Principles (Reminder)

From `architecture.md` and `CLAUDE.md`:

✅ **DO:**
- CLI only calls Service layer
- Service layer only uses abstractions (ports)
- Infrastructure implements abstractions (adapters)
- Dependency flow: CLI → Services → Abstractions ← Infra

❌ **DON'T:**
- CLI calling Repository, Provider, or any abstraction directly
- CLI importing from `treeline.infra`
- Service calling implementation-specific methods
- Leaky abstractions that expose technology details

## Success Metrics

When all tasks complete:
- [ ] Zero CLI imports from `treeline.infra`
- [ ] Zero CLI calls to `container.repository()` or `container.provider_registry()`
- [ ] All CLI commands only interact with Service layer
- [ ] All Service methods only use abstracted interfaces
- [ ] All abstractions properly hide implementation details
- [ ] Directory structure matches architecture.md
- [ ] All unit tests pass
- [ ] All smoke tests pass
- [ ] Manual testing of affected commands confirms functionality

## Notes

These tasks restore full hexagonal architecture compliance. They are surgical fixes that don't require large refactors. The codebase already has good patterns - we're just making a few commands consistent with those patterns.
