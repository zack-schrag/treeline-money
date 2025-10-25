# Code Review Tasks - January 2025

## Overview
This directory contains tasks identified during architectural review on 2025-01-24.

**Overall Assessment**: Architecture has **CRITICAL VIOLATIONS** of hexagonal principles. Commands contain business logic orchestration that must move to service layer.

## Task Summary

| Task | Priority | Status | Estimated Lines | Risk |
|------|----------|--------|----------------|------|
| [001_extract_cli_helpers.md](./001_extract_cli_helpers.md) | HIGH | 🔴 Not Started | ~60-70 removed | Low |
| [007_refactor_service_orchestration.md](./007_refactor_service_orchestration.md) | **CRITICAL** | 🔴 Not Started | Logic moved to services | High |
| [006_extract_commands_from_cli.md](./006_extract_commands_from_cli.md) | HIGH | 🔴 Not Started | ~600-700 moved | Medium |
| [002_create_shared_modals.md](./002_create_shared_modals.md) | MEDIUM | 🔴 Not Started | ~40 removed | Low |
| [003_extract_cli_display_helpers.md](./003_extract_cli_display_helpers.md) | MEDIUM | 🔴 Not Started | ~150-200 moved | Low-Medium |
| [004_extract_streaming_logic.md](./004_extract_streaming_logic.md) | LOW-MEDIUM | 🔴 Not Started | ~50-100 moved | Medium |
| [005_cleanup_todos.md](./005_cleanup_todos.md) | LOW | 🔴 Not Started | ~5-20 changed | Very Low |

## Recommended Order

### Phase 1: Foundation (MUST DO)
1. **Task 001** - Extract CLI Helpers (HIGH)
   - Affects most files
   - Foundation for all other tasks
   - Low risk, high impact

### Phase 2: Critical Architecture Fix (BLOCKING)
2. **Task 007** - Refactor Service Orchestration (**CRITICAL**)
   - Move business logic from commands to service layer
   - Fix hexagonal architecture violations
   - High risk, high complexity
   - **MUST BE DONE - This is core architectural violation**
   - Start with import command as proof of concept

### Phase 3: Command Organization (HIGH)
3. **Task 006** - Extract Commands from cli.py (HIGH)
   - Moves ~600-700 lines to commands/ folder
   - Makes cli.py a proper thin routing layer
   - Medium risk, requires Task 001 and 007 first

### Phase 4: Additional Cleanup (RECOMMENDED)
4. **Task 002** - Create Shared Modals (MEDIUM)
   - Independent from other tasks
   - Low risk

5. **Task 003** - Extract Display Helpers (MEDIUM)
   - Further reduces CLI file size
   - Optional but recommended

### Phase 5: Optional Refinements
6. **Task 004** - Extract Streaming Logic (LOW-MEDIUM)
   - Optional refinement
   - Can be done if time permits

7. **Task 005** - Cleanup TODOs (LOW)
   - Minor fixes
   - Good for end of session

## Power Session Usage

These tasks are designed for a power session workflow:
1. Create a branch: `git checkout -b code-review-refactor`
2. Work through tasks in order
3. Run tests after each task
4. Commit after each successful task
5. Create PR when complete

## Expected Outcomes

### Code Quality
- **Before**: 130+ lines of duplicated helper code
- **After**: Centralized, reusable utilities

### CLI Size (Major Improvement)
- **Before**: `cli.py` = 1540 lines (routing + implementation mixed)
- **After Task 001**: `cli.py` = 1540 lines (helpers extracted to shared module)
- **After Task 006**: `cli.py` = ~700-900 lines (commands extracted to commands/)
- **After All Tasks**: `cli.py` = ~500-700 lines (pure routing layer)

### Architectural Compliance (CRITICAL FIX)
- **Before**: Commands contain business logic orchestration (hexagonal violation)
- **After Task 007**: Service layer contains all orchestration, commands are thin display layer
- **After Task 006**: cli.py is proper routing layer, all display logic in commands/

### Maintainability
- Single source of truth for helpers
- Easier to test utilities in isolation
- Clearer separation of concerns
- Commands organized in dedicated modules

## Architecture Validation

### ✅ **Compliant Areas**:
- Storage abstractions properly used
- Domain models centralized in `domain.py`
- Dependency flow correct (inward to domain)

### 🔴 **CRITICAL VIOLATIONS** (Task 007):
- **Commands contain orchestration logic** - Multiple service calls chained together
- **Example**: `import_csv.py` orchestrates: get accounts → detect columns → preview → check duplicates → import
- **Impact**: Business workflow logic is in presentation layer (wrong layer)
- **Fix Required**: Move orchestration to service layer, commands should only display

### ⚠️ **Maintenance Issues** (Tasks 001-006):
- Code duplication (DRY violations)
- File organization (large files)
- Command implementations in cli.py instead of commands/
- Minor incomplete TODOs

## Testing Strategy

After each task:
```bash
# Run unit tests
uv run pytest tests/unit

# Run smoke tests
uv run pytest tests/smoke

# Verify specific functionality
uv run tl --help  # Verify CLI still works
```

## Notes

- All tasks are **refactoring only** - no new features
- **Task 007 is HIGH RISK** - refactors business logic flow
- Other tasks are **low-medium risk** - no logic changes
- Tests should pass after each task
- **Task 007 is BLOCKING** - must be done before other architectural fixes
- Tasks 002-006 can be done incrementally (optional refinements)

## Questions?

Refer to original architecture review or consult [architecture.md](../../architecture.md) for hexagonal architecture principles.
